export interface Quote {
  text: string;
  author: string;
}

export const INSPIRATIONAL_QUOTES: readonly Quote[] = [
  { text: "El buen cocinero es un artista que expresa su pasión a través del plato.", author: "Auguste Escoffier" },
  { text: "La creatividad es no copiar, es reinventar la experiencia y la emoción.", author: "Ferran Adrià" },
  { text: "La única forma de hacer un gran trabajo es amar profundamente lo que haces.", author: "Steve Jobs" },
  { text: "Las habilidades se pueden enseñar; la pasión y el carácter, o se tienen o no se tienen.", author: "Anthony Bourdain" },
  { text: "La mejor manera de predecir el futuro de tu negocio es tener la audacia de crearlo hoy.", author: "Peter Drucker" },
  { text: "No nos atrevemos a muchas cosas porque son difíciles; son difíciles porque no nos atrevemos.", author: "Séneca" },
  { text: "La calidad de tus pensamientos y tu foco diario determina la calidad de tu vida.", author: "Marco Aurelio" },
  { text: "Si quieres llegar a la cima de la excelencia, debes estar dispuesto a trabajar con más disciplina que nadie.", author: "Gordon Ramsay" },
  { text: "La manera de empezar es dejar de hablar y ponerse a actuar con paso firme.", author: "Walt Disney" },
  { text: "Somos lo que hacemos día tras día; de modo que la excelencia no es un acto aislado, sino un hábito.", author: "Aristóteles" },
  { text: "La técnica culinaria clásica es la base, pero el corazón de un restaurante rentable es la constancia.", author: "Paul Bocuse" },
  { text: "Una gran comida nunca es solo comida; es una experiencia que deja una memoria imborrable.", author: "Thomas Keller" },
  { text: "La disciplina es el puente inquebrantable entre los sueños y los resultados tangibles.", author: "Jim Rohn" },
  { text: "Siempre parece imposible hasta que alguien con determinación lo hace realidad.", author: "Nelson Mandela" },
  { text: "Un objetivo sin un plan de acción riguroso es simplemente una ilusión.", author: "Antoine de Saint-Exupéry" },
  { text: "La simplicidad y el cuidado por el detalle son la máxima expresión de la sofisticación.", author: "Leonardo da Vinci" },
  { text: "Nuestra mayor gloria no es no haber caído nunca, sino levantarnos con más fuerza en cada caída.", author: "Confucio" },
  { text: "El éxito en la cocina y en la empresa radica en el respeto absoluto a los ingredientes y a las personas.", author: "Alain Ducasse" },
  { text: "Hacer lo mejor en este preciso momento te sitúa en el lugar más favorable para el instante siguiente.", author: "Maya Angelou" },
  { text: "La consistencia y el control en cada proceso transforman el esfuerzo diario en una obra de arte.", author: "Massimo Bottura" },
  { text: "La inversión en orden, capacitación y control siempre paga los mejores rendimientos.", author: "Benjamin Franklin" },
  { text: "El verdadero liderazgo no consiste en mandar, sino en inspirar a tu equipo a alcanzar la excelencia.", author: "Simon Sinek" },
  { text: "En medio de cada dificultad siempre reside una enorme oportunidad de superación.", author: "Albert Einstein" },
  { text: "No cuentes los días; haz que cada uno de ellos cuente y sume a tu propósito.", author: "Muhammad Ali" },
  { text: "La excelencia nunca es un accidente; es el fruto de la intención, el esfuerzo y la ejecución inteligente.", author: "John Ruskin" }
];

export function getRandomQuote(excludeIndex?: number): Quote {
  const fallbackQuote: Quote = { text: "La excelencia es un hábito diario.", author: "Oppy" };
  if (INSPIRATIONAL_QUOTES.length === 0) {
    return fallbackQuote;
  }
  if (INSPIRATIONAL_QUOTES.length === 1) {
    return INSPIRATIONAL_QUOTES[0] ?? fallbackQuote;
  }
  let newIndex = Math.floor(Math.random() * INSPIRATIONAL_QUOTES.length);
  if (excludeIndex !== undefined && newIndex === excludeIndex) {
    newIndex = (newIndex + 1) % INSPIRATIONAL_QUOTES.length;
  }
  return INSPIRATIONAL_QUOTES[newIndex] ?? INSPIRATIONAL_QUOTES[0] ?? fallbackQuote;
}
