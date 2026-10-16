import Link from "next/link";



export default function Home() {
  return (
    <main className="site-shell">
      <nav className="site-nav" aria-label="Main navigation">
        <Link className="wordmark" href="/" aria-label="Kyro home">
          <span className="wordmark-mark">K</span> kyro
        </Link>
        <Link className="nav-login" href="/login">Log in <span aria-hidden="true">→</span></Link>
      </nav>

      <section className="hero" aria-labelledby="hero-heading">
        <div className="hero-copy">
          <p className="overline">A CALMER WAY TO CREATE</p>
          <h1 id="hero-heading">Make room for<br /><em>better ideas.</em></h1>
          <p className="hero-description">
            Kyro gives your team a focused home for the work that matters—without the noise.
          </p>
          <div className="hero-actions">
            <Link className="primary-link" href="/login">Get started <span aria-hidden="true">→</span></Link>
            <a className="text-link" href="#how-it-works">See how it works</a>
          </div>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="sun" />
          <div className="cloud cloud-one" />
          <div className="cloud cloud-two" />
          <div className="art-card card-back" />
          <div className="art-card card-front">
            <div className="card-topline" />
            <div className="card-line wide" />
            <div className="card-line" />
            <div className="card-line short" />
            <div className="card-chip">focused</div>
          </div>
          <div className="plant"><i /><i /><i /></div>
        </div>
      </section>

      <section className="feature-strip" id="how-it-works">
        <p><span>01</span> Make a little space</p>
        <p><span>02</span> Find your flow</p>
        <p><span>03</span> Build something lovely</p>
      </section>
    </main>
  );
}
