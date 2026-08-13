// Affichage du score avec code couleur + valeur numerique toujours visible
// (accessibilite : la couleur seule ne porte jamais l'information).

export function scoreColor(score: number): string {
  if (score >= 90) return "var(--color-score-excellent)";
  if (score >= 75) return "var(--color-score-good)";
  if (score >= 60) return "var(--color-score-medium)";
  return "var(--color-score-low)";
}

export function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Bon";
  if (score >= 60) return "Moyen";
  return "Faible";
}

export default function ScoreBadge({ score }: { score: number }) {
  return (
    <span className="badge" style={{ background: scoreColor(score) }} title={`Score ${scoreLabel(score)}`}>
      {Math.round(score)}/100 &middot; {scoreLabel(score)}
    </span>
  );
}
