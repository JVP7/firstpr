import { Link } from 'react-router-dom'

export default function Terms() {
  return (
    <article className="prose">
      <div className="page-head">
        <h1>Terms of service</h1>
        <p>The rules for using Starpull. Last updated November 18, 2026.</p>
      </div>

      <section className="section">
        <h2>What Starpull is</h2>
        <p>
          A free tool that lists open issues from public GitHub projects and matches them to the packages you use. Issue
          data comes from GitHub and can be a few hours out of date, so check the issue on GitHub before you start work.
        </p>
      </section>

      <section className="section">
        <h2>Who can use it</h2>
        <ul>
          <li>You must be 13 or older, the same minimum as GitHub.</li>
          <li>One account per GitHub account. Keep your password to yourself; you're responsible for what happens under your account.</li>
        </ul>
      </section>

      <section className="section">
        <h2>What you can't do</h2>
        <ul>
          <li>Try to get into other people's accounts or data.</li>
          <li>Attack, overload or scrape the site, or get around its limits.</li>
          <li>Use team names or anything else you type here to harass people.</li>
        </ul>
        <p>We may remove an account that breaks these rules.</p>
      </section>

      <section className="section">
        <h2>No guarantees</h2>
        <p>
          Starpull is a student project, provided as is, without warranties. We aren't responsible for the projects or
          issues it links to, or for losses from using it. The site may change or shut down.
        </p>
      </section>

      <section className="section">
        <h2>Changes and leaving</h2>
        <p>
          If these terms change, the date above changes too, and using Starpull after that means you accept them. You can
          delete your account any time in <Link to="/account">Account settings</Link>. How we handle your data is in
          the <Link to="/privacy">Privacy &amp; security</Link> page.
        </p>
      </section>
    </article>
  )
}
