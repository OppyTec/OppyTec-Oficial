"""
oppytec-backend/tests/unit/test_i18n_fx_and_realtime.py
Suite Unitaria Exhaustiva (Co-Creación 1:1 Fase 3 — Agente 07):
1. Motor `i18n` (`translator.py` y `dynamic_field_sync.py`):
   - Resolución `Accept-Language` / preferencia de usuario y paridad de interpolación `{{variable}}`.
   - Filtro Inmutable `"Pollo King"` (`is_proper_noun_protected` en `proveedores`, `marcas`, `holdings`, `legal_entities`).
   - Memoria Global `i18n_translation_memory` (0 tokens en `"Bodega Central"` / `"Cono Helado de Chocolate"`).
   - Micro-prompt minimalista estilo `Pi` (`< 35` tokens) y preservación de marcas incrustadas (`"Savory"`).
2. Motor Cambiario Institucional `FX` (`providers.py`, `anomaly_guard.py`, `fx_service.py`):
   - Parsers `BCCh` y `BCE Frankfurter` en `Decimal(18, 8)` (0% `float`).
   - Triangulación exacta entre `CLP`, `USD`, `EUR`, `BRL` y `UF`.
   - Escudo Anti-Anomalías (`> 8%` / `Decimal("0.08")`) que bloquea saltos abruptos y conserva la tasa previa.
   - Override Manual Auditado por el SuperUser y conversión automática de `system_plans`.
3. Motor de Tiempo Real con WebSockets (`realtime/`):
   - Aislamiento por canal `rt:{env_ns}:{holding_id}:{tenant_id}` (cero fuga cross-tenant).
   - Filtrado RBAC de 3 niveles `<modulo>.<submodulo>.<funcion>` en servidor antes de enviar por el socket.
   - Recuperación de eventos perdidos (`catch-up` con `last_event_id`) desde el buffer circular de Redis Stream.
   - Ejecución inmediata del Kill-Switch (`SESSION_REVOKED` -> cierre `4003`) y handshake JWT en `/api/v1/ws/realtime`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.core.fx import (
    FxQuote,
    FXService,
    evaluate_fx_rate_drift,
    parse_bcch_mindicador_payload,
    parse_ecb_frankfurter_payload,
)
from src.core.i18n import (
    DynamicFieldTranslationSync,
    I18nCatalogTranslator,
    build_pi_translation_prompt,
    compute_i18n_source_hash,
    is_proper_noun_protected,
    resolve_language,
    t,
)
from src.core.realtime import (
    RealtimeConnectionManager,
    RealtimeEventEnvelope,
    RealtimePublisher,
    WebSocketConnectionContext,
    build_realtime_channel,
    create_realtime_jwt_token,
    get_realtime_manager,
    get_realtime_publisher,
)
from src.core.realtime import (
    router as realtime_router,
)


@dataclass
class FakeWebSocket:
    """Doble de transporte WebSocket en memoria para verificar envíos y cierres."""

    sent_frames: list[dict[str, object]] = field(default_factory=list)
    closed_code: int | None = None
    closed_reason: str | None = None

    async def send_json(self, data: dict[str, object]) -> None:
        self.sent_frames.append(data)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed_code = code
        self.closed_reason = reason


# ============================================================================
# 1. TESTS DE INTERNACIONALIZACIÓN (ESTÁTICO + DINÁMICO "POLLO KING" + PATRÓN PI)
# ============================================================================


def test_resolve_language_from_preference_and_accept_language_header() -> None:
    """Verifica resolución de idioma desde preferencia del usuario y cabecera HTTP Accept-Language."""
    assert resolve_language(accept_language="en-US,en;q=0.9,es;q=0.8") == "en"
    assert resolve_language(accept_language="fr-FR,es-CL;q=0.9,en;q=0.7") == "es"
    assert resolve_language(accept_language="pt-BR,de-DE;q=0.8") == "es"
    assert (
        resolve_language(
            accept_language="es-CL,es;q=0.9",
            user_preferred_language="en-US",
        )
        == "en"
    )
    assert resolve_language(accept_language=None, user_preferred_language=None) == "es"


def test_static_translator_interpolates_variables_in_es_and_en() -> None:
    """Verifica interpolación determinista `{{variable}}` en los catálogos JSON `es` y `en`."""
    translator = I18nCatalogTranslator()

    es_msg = translator.translate(
        "common:greetings.welcome_user",
        lang="es",
        params={"userName": "Camila", "roleName": "Propietario"},
    )
    en_msg = translator.translate(
        "common:greetings.welcome_user",
        lang="en",
        params={"userName": "Camila", "roleName": "Owner"},
    )
    assert es_msg == "Hola, Camila (Propietario)"
    assert en_msg == "Hello, Camila (Owner)"

    err_es = t(
        "errors:rbac.permission_denied",
        lang="es",
        params={"requiredPermission": "inventory.mermas.approve"},
    )
    err_en = t(
        "errors:rbac.permission_denied",
        lang="en",
        params={"requiredPermission": "inventory.mermas.approve"},
    )
    assert "inventory.mermas.approve" in err_es
    assert "inventory.mermas.approve" in err_en


def test_pollo_king_proper_noun_guard_protects_suppliers_brands_and_holdings() -> None:
    """
    Garantiza que 'Pollo King', marcas comerciales y tablas de nombres propios (`proveedores`,
    `marcas`, `holdings`, `legal_entities`) jamás se traduzcan.
    """
    assert is_proper_noun_protected("Pollo King") is True
    assert is_proper_noun_protected("Savory") is True
    assert is_proper_noun_protected("Distribuidora Central", table_name="proveedores") is True
    assert is_proper_noun_protected("Inversiones Gastronómicas SpA", table_name="public.legal_entities") is True
    assert is_proper_noun_protected("Grupo Oppy", table_name="holdings") is True
    assert is_proper_noun_protected('"Marca Secreta"') is True
    assert is_proper_noun_protected("Helado Especial®") is True
    assert is_proper_noun_protected("Helado de Chocolate", table_name="productos") is False

    sync_engine = DynamicFieldTranslationSync()
    pollo_res = sync_engine.sync_field(
        "Pollo King",
        source_lang="es",
        active_locales=("es", "en"),
        table_name="proveedores",
    )
    assert pollo_res.proper_noun_protected is True
    assert pollo_res.tokens_consumed == 0
    assert pollo_res.credits_deducted == 0
    assert pollo_res.i18n_data == {"es": "Pollo King", "en": "Pollo King"}


def test_dynamic_field_sync_memory_hit_and_pi_micro_prompt_on_edit() -> None:
    """
    Verifica:
    1. Deduplicación SHA-256 contra `i18n_translation_memory` con 0 tokens para 'Bodega Central' y
       re-sincronización al editar 'Helado de Chocolate' -> 'Cono Helado de Chocolate'.
    2. Generación de micro-prompt estilo `Pi` (< 35 tokens) y preservación de marca incrustada ('Savory').
    """
    sync_engine = DynamicFieldTranslationSync()

    # Término repetido en gastronomía -> 0 tokens consumidos desde memoria global
    bodega_res = sync_engine.sync_field("Bodega Central", source_lang="es", active_locales=("es", "en"))
    assert bodega_res.memory_hit is True
    assert bodega_res.tokens_consumed == 0
    assert bodega_res.credits_deducted == 0
    assert bodega_res.i18n_data["en"] == "Central Warehouse"

    # Creación inicial y posterior edición por el cliente -> cambia el hash y actualiza traducción
    created = sync_engine.sync_field("Helado de Chocolate", source_lang="es", active_locales=("es", "en"))
    assert created.i18n_data["en"] == "Chocolate Ice Cream"

    edited = sync_engine.sync_field(
        "Cono Helado de Chocolate",
        source_lang="es",
        active_locales=("es", "en"),
        existing_i18n_data=created.i18n_data,
        existing_source_hash=created.i18n_source_hash,
    )
    assert edited.i18n_source_hash != created.i18n_source_hash
    assert edited.i18n_data["en"] == "Chocolate Ice Cream Cone"
    assert edited.tokens_consumed == 0

    # Término compuesto con marca comercial registrada incrustada ("Helado de Chocolate Savory")
    composite = sync_engine.sync_field(
        "Helado de Chocolate Savory",
        source_lang="es",
        active_locales=("es", "en"),
    )
    assert composite.memory_hit is False
    assert composite.tokens_consumed < 35
    assert composite.credits_deducted == 0
    assert composite.i18n_data["en"] == "Chocolate Ice Cream Savory"
    assert composite.pi_prompt_used is not None
    assert "keep=[Savory]" in composite.pi_prompt_used

    # Segunda vez que cualquier Tenant usa el mismo término compuesto -> Memory Hit en 0 tokens
    composite_cached = sync_engine.sync_field(
        "Helado de Chocolate Savory",
        source_lang="es",
        active_locales=("es", "en"),
    )
    assert composite_cached.memory_hit is True
    assert composite_cached.tokens_consumed == 0
    assert composite_cached.i18n_source_hash == compute_i18n_source_hash("Helado de Chocolate Savory", "es")

    prompt = build_pi_translation_prompt(
        "Salsa de la Casa",
        source_lang="es",
        target_langs=("en",),
        protected_brands=("Savory",),
    )
    assert len(prompt.split()) < 20


# ============================================================================
# 2. TESTS DE MULTI-MONEDA FX (BCCh + BCE DECIMAL, ANOMALY GUARD > 8%, OVERRIDE)
# ============================================================================


def test_bcch_and_ecb_frankfurter_parsers_return_strict_decimal() -> None:
    """Verifica que los parsers del BCCh y BCE produzcan exclusivamente instancias `Decimal(18, 8)`."""
    bcch_payload: dict[str, object] = {
        "dolar": {"valor": "948.50"},
        "euro": {"valor": "1032.40"},
        "uf": {"valor": "37985.12"},
    }
    bcch_quotes = parse_bcch_mindicador_payload(bcch_payload)
    assert len(bcch_quotes) == 3
    by_pair = {q.currency_pair: q for q in bcch_quotes}
    assert by_pair["USD/CLP"].rate == Decimal("948.50000000")
    assert by_pair["EUR/CLP"].rate == Decimal("1032.40000000")
    assert by_pair["UF/CLP"].rate == Decimal("37985.12000000")

    ecb_payload: dict[str, object] = {
        "base": "EUR",
        "rates": {"USD": "1.0875", "BRL": "6.1125"},
    }
    ecb_quotes = parse_ecb_frankfurter_payload(ecb_payload)
    ecb_by_pair = {q.currency_pair: q for q in ecb_quotes}
    assert ecb_by_pair["EUR/USD"].rate == Decimal("1.08750000")
    assert ecb_by_pair["EUR/BRL"].rate == Decimal("6.11250000")


def test_fx_anomaly_guard_quarantines_jumps_above_8_percent() -> None:
    """Verifica que saltos > 8% sin confirmación secundaria sean puestos en cuarentena."""
    prev_rate = Decimal("950.00000000")
    normal_candidate = Decimal("965.00000000")  # +1.58%
    anomalous_candidate = Decimal("1080.00000000")  # +13.68% (> 8%)

    ok_eval = evaluate_fx_rate_drift("USD/CLP", prev_rate, normal_candidate)
    assert ok_eval.is_quarantined is False
    assert ok_eval.effective_rate == normal_candidate
    assert ok_eval.action_taken == "AUTO_UPDATED"

    blocked_eval = evaluate_fx_rate_drift("USD/CLP", prev_rate, anomalous_candidate)
    assert blocked_eval.is_quarantined is True
    assert blocked_eval.effective_rate == prev_rate
    assert blocked_eval.action_taken == "FX_ANOMALY_QUARANTINED"
    assert blocked_eval.alert_message is not None

    confirmed_eval = evaluate_fx_rate_drift(
        "USD/CLP",
        prev_rate,
        anomalous_candidate,
        confirmed_by_secondary_source=True,
    )
    assert confirmed_eval.is_quarantined is False
    assert confirmed_eval.effective_rate == anomalous_candidate


def test_fx_service_triangulation_manual_override_and_plan_prices() -> None:
    """
    Verifica triangulación `Decimal` entre `CLP`, `USD`, `EUR`, `BRL` y `UF`,
    override manual auditado del SuperUser y conversión automática de precios de planes.
    """
    fx = FXService(seed_default_rates=True)

    # Conversión directa e inversa en Decimal
    clp_from_usd = fx.convert_amount(Decimal("100.00"), "USD", "CLP")
    assert clp_from_usd == Decimal("95000.00")

    clp_integer = fx.convert_amount(Decimal("10.50"), "USD", "CLP", integer_clp=True)
    assert clp_integer == Decimal("9975")

    # Triangulación CLP -> BRL (vía USD/EUR) y UF -> USD (vía CLP)
    brl_amount = fx.convert_amount(Decimal("95000.00"), "CLP", "BRL")
    assert brl_amount == Decimal("560.00")

    usd_from_uf = fx.convert_amount(Decimal("1.00"), "UF", "USD")
    assert usd_from_uf == Decimal("39.95")

    # Intento de actualización automática anómala (> 8%) -> se bloquea y genera auditoría
    bad_quote = FxQuote(
        base_currency="USD",
        quote_currency="CLP",
        rate=Decimal("1200.00000000"),
        source_provider="BCCH_OFFICIAL",
        effective_date=datetime.now(tz=UTC),
    )
    drift_res = fx.ingest_automatic_quote(bad_quote)
    assert drift_res.is_quarantined is True
    assert fx.get_exchange_rate("USD", "CLP") == Decimal("950.00000000")
    assert len(fx.audit_logs) == 1
    assert fx.audit_logs[0].action_taken == "FX_ANOMALY_QUARANTINED"

    # Override Manual Auditado por el SuperUser
    audit_entry = fx.apply_manual_fx_override(
        "USD",
        "CLP",
        Decimal("960.00000000"),
        actor_user_id=1,
        reason="Ajuste manual tesorería corporativa OppyTec cierre mensual",
        is_superuser=True,
    )
    assert audit_entry.previous_rate == Decimal("950.00000000")
    assert audit_entry.new_rate == Decimal("960.00000000")
    assert audit_entry.actor_user_id == 1
    assert fx.get_exchange_rate("USD", "CLP") == Decimal("960.00000000")

    # Conversión de precios de system_plans
    plan_matrix = fx.convert_system_plan_prices(Decimal("100.00"), anchor_currency="USD")
    assert plan_matrix["price_usd"] == Decimal("100.00")
    assert plan_matrix["price_clp"] == Decimal("96000.00")
    assert plan_matrix["price_brl"] == Decimal("560.00")


# ============================================================================
# 3. TESTS DE TIEMPO REAL WEBSOCKETS (AISLAMIENTO TENANT, RBAC 3-NIVELES, CATCH-UP Y KILL-SWITCH)
# ============================================================================


@pytest.mark.asyncio
async def test_realtime_manager_enforces_tenant_isolation_and_3_level_rbac() -> None:
    """
    Verifica que un evento de `tenant_a` jamás llegue a `tenant_b` y que dentro del mismo
    `tenant_a` solo reciban el frame quienes posean el permiso RBAC de 3 niveles requerido.
    """
    manager = RealtimeConnectionManager(default_env_ns="wt_p3_3")
    publisher = RealtimePublisher(manager, env_ns="wt_p3_3")

    holding_id = uuid4()
    tenant_a = uuid4()
    tenant_b = uuid4()

    ws_supervisor_a = FakeWebSocket()
    ws_cashier_a = FakeWebSocket()
    ws_supervisor_b = FakeWebSocket()

    ctx_supervisor_a = WebSocketConnectionContext(
        websocket=ws_supervisor_a,
        user_id=10,
        holding_id=holding_id,
        tenant_id=tenant_a,
        env_ns="wt_p3_3",
        active_permissions=frozenset({"inventory.mermas.approve", "inventory.stock.view"}),
    )
    ctx_cashier_a = WebSocketConnectionContext(
        websocket=ws_cashier_a,
        user_id=11,
        holding_id=holding_id,
        tenant_id=tenant_a,
        env_ns="wt_p3_3",
        active_permissions=frozenset({"operations.pos.sell"}),
    )
    ctx_supervisor_b = WebSocketConnectionContext(
        websocket=ws_supervisor_b,
        user_id=20,
        holding_id=holding_id,
        tenant_id=tenant_b,
        env_ns="wt_p3_3",
        active_permissions=frozenset({"inventory.mermas.approve"}),
    )

    ch_a = manager.register(ctx_supervisor_a)
    manager.register(ctx_cashier_a)
    manager.register(ctx_supervisor_b)
    assert ch_a == build_realtime_channel("wt_p3_3", holding_id, tenant_a)

    envelope = RealtimeEventEnvelope(
        event_type="inventory.merma.approval_requested",
        holding_id=holding_id,
        tenant_id=tenant_a,
        required_permission="inventory.mermas.approve",
        query_keys_to_invalidate=[["mermas", str(tenant_a)]],
        payload={"merma_id": 501, "item": "Lomo Vetado"},
    )
    published = await publisher.publish_event(envelope)

    assert published.event_id != "0-0"
    assert len(ws_supervisor_a.sent_frames) == 1
    assert ws_supervisor_a.sent_frames[0]["event_id"] == published.event_id
    # Cajero sin permiso `inventory.mermas.approve` recibe 0 frames
    assert len(ws_cashier_a.sent_frames) == 0
    # Otro tenant recibe 0 frames
    assert len(ws_supervisor_b.sent_frames) == 0


@pytest.mark.asyncio
async def test_realtime_catchup_from_last_event_id_and_kill_switch_revocation() -> None:
    """
    Verifica la recuperación de eventos perdidos (`last_event_id`) desde el buffer circular
    y la desconexión inmediata (`code=4003`) ante el Kill-Switch `SESSION_REVOKED`.
    """
    manager = RealtimeConnectionManager(default_env_ns="wt_p3_3")
    publisher = RealtimePublisher(manager, env_ns="wt_p3_3")
    holding_id = uuid4()
    tenant_id = uuid4()

    ev1 = await publisher.publish_event(
        RealtimeEventEnvelope(
            event_id="1729271000001-0",
            event_type="inventory.stock_updated",
            holding_id=holding_id,
            tenant_id=tenant_id,
            required_permission="inventory.stock.view",
            query_keys_to_invalidate=[["stock", str(tenant_id)]],
        )
    )
    ev2 = await publisher.publish_event(
        RealtimeEventEnvelope(
            event_id="1729271000002-0",
            event_type="inventory.low_stock_alert",
            holding_id=holding_id,
            tenant_id=tenant_id,
            required_permission="inventory.stock.view",
            query_keys_to_invalidate=[["alerts", str(tenant_id)]],
        )
    )

    catchup = publisher.get_catchup_events(
        holding_id,
        tenant_id,
        last_event_id=ev1.event_id,
    )
    assert len(catchup) == 1
    assert catchup[0].event_id == ev2.event_id

    # Prueba de Kill-Switch al pasar usuario a soft-delete
    ws_worker = FakeWebSocket()
    ctx_worker = WebSocketConnectionContext(
        websocket=ws_worker,
        user_id=77,
        holding_id=holding_id,
        tenant_id=tenant_id,
        env_ns="wt_p3_3",
        active_permissions=frozenset({"inventory.stock.view"}),
    )
    manager.register(ctx_worker)

    revoked_count = await manager.revoke_user_sessions(
        user_id=77,
        holding_id=holding_id,
        tenant_id=tenant_id,
        env_ns="wt_p3_3",
    )
    assert revoked_count == 1
    assert ws_worker.closed_code == 4003
    assert ws_worker.closed_reason == "SESSION_REVOKED"
    assert manager.get_channel_connections(ctx_worker.channel) == []


def test_websocket_router_endpoint_jwt_auth_and_catchup() -> None:
    """
    Verifica el endpoint `/api/v1/ws/realtime` con `TestClient`:
    - Rechaza conexión sin JWT (`code=4001`).
    - Rechaza acceso a un `tenant_id` no autorizado (`code=4003`).
    - Acepta JWT válido, entrega eventos pendientes por `last_event_id` y responde `pong` al `ping`.
    """
    app = FastAPI()
    app.include_router(realtime_router)
    client = TestClient(app)

    holding_id = uuid4()
    authorized_tenant = uuid4()
    forbidden_tenant = uuid4()

    # 1. Sin token JWT -> se cierra con 4001
    with (
        pytest.raises(WebSocketDisconnect) as exc_no_token,
        client.websocket_connect(f"/api/v1/ws/realtime?tenant_id={authorized_tenant}"),
    ):
        pass
    assert exc_no_token.value.code == 4001

    # 2. Con token JWT válido pero para otro tenant -> se cierra con 4003
    valid_token = create_realtime_jwt_token(
        user_id=42,
        holding_id=holding_id,
        allowed_tenant_ids=[authorized_tenant],
        permissions=["inventory.stock.view"],
    )
    with (
        pytest.raises(WebSocketDisconnect) as exc_forbidden,
        client.websocket_connect(
            f"/api/v1/ws/realtime?tenant_id={forbidden_tenant}&token={valid_token}"
        ),
    ):
        pass
    assert exc_forbidden.value.code == 4003

    # 3. Publicamos dos eventos en el singleton publisher y reconectamos con last_event_id
    pub = get_realtime_publisher()
    mgr = get_realtime_manager()
    assert mgr is not None
    import asyncio

    asyncio.run(
        pub.publish_event(
            RealtimeEventEnvelope(
                event_id="1729272000001-0",
                event_type="inventory.stock_updated",
                holding_id=holding_id,
                tenant_id=authorized_tenant,
                required_permission="inventory.stock.view",
            )
        )
    )
    asyncio.run(
        pub.publish_event(
            RealtimeEventEnvelope(
                event_id="1729272000002-0",
                event_type="inventory.low_stock_alert",
                holding_id=holding_id,
                tenant_id=authorized_tenant,
                required_permission="inventory.stock.view",
            )
        )
    )

    with client.websocket_connect(
        f"/api/v1/ws/realtime?tenant_id={authorized_tenant}&token={valid_token}&last_event_id=1729272000001-0"
    ) as ws:
        catchup_frame = ws.receive_json()
        assert catchup_frame["event_id"] == "1729272000002-0"
        assert catchup_frame["event_type"] == "inventory.low_stock_alert"

        ws.send_json({"type": "ping"})
        pong_frame = ws.receive_json()
        assert pong_frame["type"] == "pong"
