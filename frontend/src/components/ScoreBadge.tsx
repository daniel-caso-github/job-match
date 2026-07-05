import { scoreColors } from "../lib/score";

interface Props {
  score: number | null;
  variant?: "card" | "hero";
}

export default function ScoreBadge({ score, variant = "card" }: Props) {
  const sc = scoreColors(score);
  const isHero = variant === "hero";
  return (
    <div
      className={`flex flex-col items-center justify-center shrink-0 border ${
        isHero ? "w-[104px] h-[104px] rounded-2xl" : "w-[76px] h-16 rounded-xl"
      } ${sc.bg} ${sc.border}`}
    >
      <span
        className={`font-mono font-bold leading-none ${isHero ? "text-[42px]" : "text-[26px]"} ${sc.fg}`}
      >
        {sc.text}
      </span>
      <span
        className={`uppercase ${
          isHero
            ? "text-[11px] tracking-[0.1em] mt-1.5 opacity-80"
            : "text-[10px] tracking-[0.08em] mt-[3px] opacity-75"
        } ${sc.fg}`}
      >
        {isHero ? "Score LLM" : "LLM"}
      </span>
    </div>
  );
}
