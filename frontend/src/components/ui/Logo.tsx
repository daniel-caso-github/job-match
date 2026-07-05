interface LogoProps {
  size?: number;
  radius?: number;
  fontSize?: number;
}

export default function Logo({ size = 26, radius = 7, fontSize = 14 }: LogoProps) {
  return (
    <div
      className="flex items-center justify-center font-bold text-[#0a0b0d] select-none"
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        fontSize,
        background: "linear-gradient(135deg,#818cf8,#6366f1)",
      }}
    >
      J
    </div>
  );
}
