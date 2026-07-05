import { formatTime } from "../lib/format";
import { formatDuration, stageState, type StageState } from "../lib/pipeline";
import type { PipelineTask } from "../types/api";
import { CheckIcon, XIcon } from "./ui/icons";

const PIPELINE_STAGES = ["recolectar", "extraer_requisitos", "embeddings", "score_perfiles"];

const STAGE_COLOR: Record<StageState, string> = {
  success: "var(--pos)",
  running: "var(--accent)",
  failed: "var(--neg)",
  pending: "var(--border3)",
};

interface StageView {
  label: string;
  state: StageState;
  statusText: string;
  span: string;
}

export function stageViews(tasks: PipelineTask[]): StageView[] {
  if (tasks.length === 0) {
    return PIPELINE_STAGES.map((label) => ({
      label,
      state: "pending",
      statusText: "pendiente",
      span: "—",
    }));
  }
  return tasks.map((task) => {
    const state = stageState(task);
    const statusText =
      state === "success"
        ? formatDuration(task.duration)
        : state === "running"
          ? "corriendo"
          : state === "failed"
            ? "falló"
            : "pendiente";
    const span = task.start_date
      ? `${formatTime(task.start_date)} → ${formatTime(task.end_date)}`
      : "—";
    return { label: task.task_id, state, statusText, span };
  });
}

function progressWidth(stages: StageView[]): string {
  const n = stages.length;
  if (n <= 1) return "0%";
  let filled = 0;
  for (let i = 0; i < n - 1; i++) {
    if (stages[i].state === "success") filled++;
  }
  return `${(filled / (n - 1)) * 75}%`;
}

function StageNode({ stage }: { stage: StageView }) {
  const color = STAGE_COLOR[stage.state];
  return (
    <div
      className="relative z-[1] w-[30px] h-[30px] rounded-full bg-panel flex items-center justify-center"
      style={{ border: `2px solid ${color}` }}
    >
      {stage.state === "success" && (
        <span className="w-3.5 h-3.5 text-pos">
          <CheckIcon size={14} />
        </span>
      )}
      {stage.state === "running" && (
        <span className="w-3.5 h-3.5 text-accent animate-spin">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
          </svg>
        </span>
      )}
      {stage.state === "failed" && (
        <span className="w-[13px] h-[13px] text-neg">
          <XIcon size={13} />
        </span>
      )}
      {stage.state === "pending" && (
        <span className="w-[7px] h-[7px] rounded-full bg-line-3" />
      )}
    </div>
  );
}

interface StageStepperProps {
  tasks: PipelineTask[];
}

export default function StageStepper({ tasks }: StageStepperProps) {
  const stages = stageViews(tasks);
  return (
    <div className="relative">
      <div className="absolute top-3.5 left-[12.5%] right-[12.5%] h-0.5 bg-line-2 rounded-sm" />
      <div
        className="absolute top-3.5 left-[12.5%] h-0.5 bg-pos rounded-sm"
        style={{ width: progressWidth(stages) }}
      />
      <div className="relative flex">
        {stages.map((stage) => (
          <div key={stage.label} className="flex-1 flex flex-col items-center gap-2">
            <StageNode stage={stage} />
            <div className="text-center">
              <div
                className={`font-mono text-[11px] ${
                  stage.state === "pending" ? "text-muted" : "text-fg-2"
                }`}
              >
                {stage.label}
              </div>
              <div
                className="text-[10px] mt-0.5"
                style={{
                  color: stage.state === "pending" ? "var(--muted)" : STAGE_COLOR[stage.state],
                }}
              >
                {stage.statusText}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function StageRows({ tasks }: { tasks: PipelineTask[] }) {
  const stages = stageViews(tasks);
  return (
    <div className="flex flex-col gap-0.5">
      {stages.map((stage) => (
        <div
          key={stage.label}
          className="flex items-center gap-3 px-3.5 py-[9px] bg-app border border-hair rounded-[9px]"
        >
          <span
            className="w-2 h-2 flex-none rounded-full"
            style={{ background: STAGE_COLOR[stage.state] }}
          />
          <span
            className={`flex-1 font-mono text-xs ${
              stage.state === "pending" ? "text-muted" : "text-fg-2"
            }`}
          >
            {stage.label}
          </span>
          <span className="font-mono text-[11px] text-muted">{stage.span}</span>
          <span
            className="text-[11px] font-medium min-w-[60px] text-right"
            style={{
              color: stage.state === "pending" ? "var(--muted)" : STAGE_COLOR[stage.state],
            }}
          >
            {stage.statusText}
          </span>
        </div>
      ))}
    </div>
  );
}
