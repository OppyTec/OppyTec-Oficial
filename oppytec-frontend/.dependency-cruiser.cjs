/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-circular-dependencies",
      severity: "error",
      comment:
        "Prohibido introducir dependencias circulares en oppytec-frontend (Clean Feature-Driven Architecture).",
      from: {},
      to: {
        circular: true,
      },
    },
    {
      name: "no-cross-feature-imports",
      severity: "error",
      comment:
        "Los módulos en src/features/* no pueden importarse directamente entre sí; toda dependencia compartida debe residir en src/shared/*.",
      from: {
        path: "^src/features/([^/]+)/",
      },
      to: {
        path: "^src/features/([^/]+)/",
        pathNot: "^src/features/$1/",
      },
    },
    {
      name: "shared-must-not-import-features",
      severity: "error",
      comment:
        "La capa transversal src/shared/* jamás puede depender de módulos de negocio en src/features/* ni de src/app/*.",
      from: {
        path: "^src/shared/",
      },
      to: {
        path: "^src/(features|app)/",
      },
    },
  ],
  options: {
    doNotFollow: {
      path: "node_modules",
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: "tsconfig.json",
    },
  },
};
