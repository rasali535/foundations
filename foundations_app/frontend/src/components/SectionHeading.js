import Reveal from "./Reveal";

export default function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  testid,
}) {
  return (
    <div
      className={`max-w-3xl ${align === "center" ? "mx-auto text-center" : ""}`}
      data-testid={testid}
    >
      {eyebrow && (
        <Reveal>
          <p className="eyebrow mb-4">{eyebrow}</p>
        </Reveal>
      )}
      <Reveal delay={0.05}>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl tracking-tight leading-[1.05] font-semibold text-[#0F172A]">
          {title}
        </h2>
      </Reveal>
      {description && (
        <Reveal delay={0.1}>
          <p className="mt-5 text-base md:text-lg text-[#475569] leading-relaxed">
            {description}
          </p>
        </Reveal>
      )}
    </div>
  );
}
