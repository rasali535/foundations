import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="section container-x text-center">
      <p className="eyebrow">404</p>
      <h1 className="mt-4 text-5xl font-semibold tracking-tight text-[#0F172A]">
        Page not found.
      </h1>
      <p className="mt-4 text-[#475569]">
        Let's get you back to something useful.
      </p>
      <Link to="/" data-testid="not-found-cta" className="btn-primary mt-8 inline-flex">
        Return home
      </Link>
    </section>
  );
}
