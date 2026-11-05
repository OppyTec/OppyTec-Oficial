/**
 * oppytec-frontend/src/features/oppyfy/__tests__/ChatFeedbackButtons.test.tsx
 * Pruebas unitarias para los componentes interactivos de feedback humano (RLHF)
 * y reporte de alucinaciones en el chat de OppyFy (React 19 + Vitest):
 * 1. Renderizado accesible con touch targets >= 44px (Mobile-First).
 * 2. Envío optimista e inmediato de feedback positivo (👍) con toast Sonner.
 * 3. Apertura del modal asistido de reporte (👎) con 5 categorías de fallo y textarea.
 * 4. Envío de reporte de fallo y alucinación con feedback negativo.
 * 5. Persistencia y estados activos de resplandor visual.
 * 6. Integración en el panel conversacional OppyfyChatPane.
 */

import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { toast } from "sonner";
import * as httpClient from "@/shared/api/httpClient";
import { PermissionsProvider, type RbacPolicyState } from "@/shared/auth/usePermissions";
import { CurrencyProvider } from "@/shared/currency";
import {
  ChatFeedbackButtons,
  FeedbackReportModal,
  OppyfyChatPane,
  calculateContextHealth,
  type ChatMessage,
} from "../index";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

const mockPolicy: RbacPolicyState = {
  roleName: "Gerente Operaciones",
  planModules: ["oppyfy", "inventory"],
  rolePermissions: ["oppyfy.workspace.query"],
  temporaryGrants: [],
  deniedPermissions: [],
  isSuperUser: true,
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <CurrencyProvider initialCurrency="CLP">
        <PermissionsProvider initialPolicy={mockPolicy}>
          {ui}
        </PermissionsProvider>
      </CurrencyProvider>
    </QueryClientProvider>
  );
}

describe("ChatFeedbackButtons & FeedbackReportModal (RLHF & Evals UI)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.clear();
    }
  });

  it("renderiza botones 👍 y 👎 con touch targets >= 44px y etiquetas ARIA accesibles", () => {
    renderWithProviders(
      <ChatFeedbackButtons messageId="msg-eval-001" traceId="trace-langfuse-001" />
    );

    const upBtn = screen.getByTestId("thumbs-up-btn-msg-eval-001");
    const downBtn = screen.getByTestId("thumbs-down-btn-msg-eval-001");

    expect(upBtn).toBeInTheDocument();
    expect(downBtn).toBeInTheDocument();

    // Cumplimiento Mobile-First: min-h-[44px] y min-w-[44px]
    expect(upBtn.className).toContain("min-h-[44px]");
    expect(upBtn.className).toContain("min-w-[44px]");
    expect(downBtn.className).toContain("min-h-[44px]");
    expect(downBtn.className).toContain("min-w-[44px]");

    // Accesibilidad ARIA
    expect(upBtn).toHaveAttribute("aria-pressed", "false");
    expect(downBtn).toHaveAttribute("aria-pressed", "false");
    expect(upBtn).toHaveAttribute("aria-label");
    expect(downBtn).toHaveAttribute("aria-label");
  });

  it("envía feedback positivo (👍) inmediatamente con rating 5 y activa el resplandor verde", async () => {
    const apiSpy = vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
      data: {
        id: "msg-eval-002",
        status: "success",
        message: "Feedback registrado",
        feedback_type: "positive",
        created_at: new Date().toISOString(),
      },
      traceId: "trace-langfuse-002",
      timestampIso: new Date().toISOString(),
      tenantId: "tenant_rest_central",
    });

    const onSubmitted = vi.fn();

    renderWithProviders(
      <ChatFeedbackButtons
        messageId="msg-eval-002"
        traceId="trace-langfuse-002"
        onFeedbackSubmitted={onSubmitted}
      />
    );

    const upBtn = screen.getByTestId("thumbs-up-btn-msg-eval-002");
    fireEvent.click(upBtn);

    await waitFor(() => {
      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/oppy_ai/chat/feedback",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            message_id: "msg-eval-002",
            trace_id: "trace-langfuse-002",
            feedback_type: "positive",
            rating: 5,
          }),
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
      expect(onSubmitted).toHaveBeenCalledWith("positive");
    });

    // Indicador visual activo
    expect(screen.getByTestId("feedback-positive-indicator")).toBeInTheDocument();
  });

  it("abre el modal de reporte al presionar 👎 con las 5 categorías de fallo estandarizadas", async () => {
    renderWithProviders(
      <ChatFeedbackButtons messageId="msg-eval-003" traceId="trace-langfuse-003" />
    );

    const downBtn = screen.getByTestId("thumbs-down-btn-msg-eval-003");
    fireEvent.click(downBtn);

    // Modal abierto con selector de categorías
    expect(screen.getByTestId("feedback-report-modal")).toBeInTheDocument();
    expect(screen.getByTestId("category-hallucination")).toBeInTheDocument();
    expect(screen.getByTestId("category-math_error")).toBeInTheDocument();
    expect(screen.getByTestId("category-incomplete")).toBeInTheDocument();
    expect(screen.getByTestId("category-bad_formatting")).toBeInTheDocument();
    expect(screen.getByTestId("category-other")).toBeInTheDocument();

    // Textarea opcional
    expect(screen.getByTestId("feedback-user-correction-input")).toBeInTheDocument();
  });

  it("permite seleccionar motivo de fallo, ingresar respuesta esperada y enviar reporte", async () => {
    const apiSpy = vi.spyOn(httpClient, "apiRequest").mockResolvedValueOnce({
      data: {
        id: "msg-eval-004",
        status: "success",
        message: "Feedback de alucinación registrado",
        feedback_type: "negative",
        failure_category: "hallucination",
        created_at: new Date().toISOString(),
      },
      traceId: "trace-langfuse-004",
      timestampIso: new Date().toISOString(),
      tenantId: "tenant_rest_central",
    });

    const onSubmitted = vi.fn();

    renderWithProviders(
      <ChatFeedbackButtons
        messageId="msg-eval-004"
        traceId="trace-langfuse-004"
        onFeedbackSubmitted={onSubmitted}
      />
    );

    // Abrir modal con 👎
    fireEvent.click(screen.getByTestId("thumbs-down-btn-msg-eval-004"));

    // Seleccionar motivo "hallucination"
    fireEvent.click(screen.getByTestId("category-hallucination"));

    // Escribir corrección de negocio
    const textarea = screen.getByTestId("feedback-user-correction-input");
    fireEvent.change(textarea, {
      target: {
        value: "Para Pollo King el stock real no es 100 kg sino 45 kg en bodega central",
      },
    });

    // Enviar formulario
    const submitBtn = screen.getByTestId("feedback-submit-btn");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiSpy).toHaveBeenCalledWith(
        "/api/v1/oppy_ai/chat/feedback",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            message_id: "msg-eval-004",
            trace_id: "trace-langfuse-004",
            feedback_type: "negative",
            failure_category: "hallucination",
            user_correction:
              "Para Pollo King el stock real no es 100 kg sino 45 kg en bodega central",
            rating: 1,
          }),
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
      expect(onSubmitted).toHaveBeenCalledWith("negative", "hallucination");
    });
  });

  it("cierra el modal sin enviar feedback al presionar 'Cancelar'", () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    renderWithProviders(
      <FeedbackReportModal
        isOpen={true}
        onClose={onClose}
        onSubmit={onSubmit}
        messageId="msg-eval-005"
      />
    );

    const cancelBtn = screen.getByTestId("feedback-cancel-btn");
    fireEvent.click(cancelBtn);

    expect(onClose).toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("renderiza con estado positivo inicial y resplandor cuando ya fue votado", () => {
    renderWithProviders(
      <ChatFeedbackButtons
        messageId="msg-eval-006"
        initialFeedback="positive"
      />
    );

    const upBtn = screen.getByTestId("thumbs-up-btn-msg-eval-006");
    expect(upBtn).toHaveAttribute("aria-pressed", "true");
    expect(upBtn.className).toContain("text-emerald-600");
    expect(screen.getByTestId("feedback-positive-indicator")).toBeInTheDocument();
  });

  it("renderiza con estado negativo inicial y resplandor cuando ya fue reportado", () => {
    renderWithProviders(
      <ChatFeedbackButtons
        messageId="msg-eval-007"
        initialFeedback="negative"
      />
    );

    const downBtn = screen.getByTestId("thumbs-down-btn-msg-eval-007");
    expect(downBtn).toHaveAttribute("aria-pressed", "true");
    expect(downBtn.className).toContain("text-destructive");
    expect(screen.getByTestId("feedback-negative-indicator")).toBeInTheDocument();
  });

  it("integra los botones de feedback debajo de respuestas del asistente en OppyfyChatPane", () => {
    const mockMessages: ChatMessage[] = [
      {
        id: "user-msg-1",
        role: "user",
        content: "¿Cuál es el costo de pechuga en Pollo King?",
        timestamp: new Date().toISOString(),
      },
      {
        id: "assistant-msg-1",
        role: "assistant",
        content: "El costo teórico de pechuga en Pollo King es $3.500 CLP por kg.",
        timestamp: new Date().toISOString(),
        traceId: "trace-chatpane-001",
      },
    ];

    renderWithProviders(
      <OppyfyChatPane
        messages={mockMessages}
        draftPrompt=""
        onChangeDraftPrompt={vi.fn()}
        onSendMessage={vi.fn()}
        isSending={false}
        contextHealth={calculateContextHealth(20)}
      />
    );

    // Mensaje de usuario NO debe tener botones de feedback
    expect(
      screen.queryByTestId("chat-feedback-buttons-user-msg-1")
    ).not.toBeInTheDocument();

    // Mensaje del asistente SÍ debe tener botones de feedback
    expect(
      screen.getByTestId("chat-feedback-buttons-assistant-msg-1")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("thumbs-up-btn-assistant-msg-1")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("thumbs-down-btn-assistant-msg-1")
    ).toBeInTheDocument();
  });
});
