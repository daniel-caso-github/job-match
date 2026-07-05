import {
  useFieldArray,
  type Control,
  type FieldErrors,
  type UseFormRegister,
} from "react-hook-form";
import type { ProfileFormValues } from "../lib/schemas";
import { PlusIcon, XIcon } from "./ui/icons";

interface Props {
  control: Control<ProfileFormValues>;
  register: UseFormRegister<ProfileFormValues>;
  errors: FieldErrors<ProfileFormValues>;
}

export default function StackInput({ control, register, errors }: Props) {
  const { fields, append, remove } = useFieldArray({ control, name: "stack" });

  return (
    <div>
      <div className="flex flex-col gap-2">
        {fields.map((field, i) => {
          const rowError = errors.stack?.[i];
          return (
            <div key={field.id}>
              <div className="flex gap-2 items-center">
                <input
                  {...register(`stack.${i}.name`)}
                  placeholder="tecnología"
                  className="flex-1 min-w-0 h-[38px] px-3 bg-panel border border-line-2 rounded-[9px] text-fg font-mono text-sm outline-none focus:border-accent"
                />
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    min={0}
                    max={40}
                    step={0.5}
                    {...register(`stack.${i}.years`, { valueAsNumber: true })}
                    className="w-[72px] h-[38px] px-2.5 bg-panel border border-line-2 rounded-[9px] text-fg font-mono text-sm text-center outline-none focus:border-accent"
                  />
                  <span className="text-[13px] text-muted">años</span>
                </div>
                <button
                  type="button"
                  onClick={() => remove(i)}
                  title="Quitar"
                  className="w-[38px] h-[38px] flex-none flex items-center justify-center bg-panel border border-line-2 rounded-[9px] text-muted hover:border-neg-line hover:text-neg transition-colors"
                >
                  <XIcon size={16} />
                </button>
              </div>
              {(rowError?.name || rowError?.years) && (
                <p className="mt-1 text-[13px] text-neg">
                  {rowError?.name?.message ?? rowError?.years?.message}
                </p>
              )}
            </div>
          );
        })}
      </div>
      {typeof errors.stack?.message === "string" && (
        <p className="mt-2 text-[13px] text-neg">{errors.stack.message}</p>
      )}
      <button
        type="button"
        onClick={() => append({ name: "", years: 0 })}
        className="inline-flex items-center gap-1.5 mt-2.5 h-[34px] px-3 bg-panel2 border border-dashed border-line-3 rounded-[9px] text-accent-text text-sm hover:border-accent transition-colors"
      >
        <PlusIcon size={14} />
        Agregar tecnología
      </button>
    </div>
  );
}
