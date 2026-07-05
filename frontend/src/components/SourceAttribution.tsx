interface Props {
  text: string;
}

export default function SourceAttribution({ text }: Props) {
  return (
    <footer className="mt-10 pt-5 border-t border-head-line">
      <p className="m-0 text-[13px] text-muted leading-relaxed">{text}</p>
    </footer>
  );
}
