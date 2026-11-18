import { Link } from 'react-router-dom'

export default function Privacy() {
  return (
    <article className="prose">
      <div className="page-head">
        <h1>Privacy &amp; security</h1>
        <p>What Starpull keeps about you, who handles it, and how to remove it. Last updated November 18, 2026.</p>
      </div>

      <section className="section">
        <h2>What we store</h2>
        <ul>
          <li><strong>Your GitHub username</strong>, confirmed by GitHub sign-in, so nobody can sign up as you.</li>
          <li><strong>Your email</strong>, as a second way to log in.</li>
          <li><strong>A one-way hash of your password</strong> (bcrypt). Nobody, including us, can read the password back.</li>
          <li><strong>Your public repos and the packages they use</strong>, plus any packages you add yourself. This is how we find matching issues.</li>
          <li><strong>The issues you save</strong> and their status, and any teams you join. Your teammates see your GitHub username and the issues you've saved.</li>
          <li><strong>Your IP address, briefly.</strong> Login and signup attempts record it to stop password guessing. Those records are deleted after an hour.</li>
        </ul>
      </section>

      <section className="section">
        <h2>What we never store</h2>
        <ul>
          <li>Your password in readable form.</li>
          <li>Your GitHub access token. Sign-in asks GitHub for no permissions; we read your public profile once and throw the token away.</li>
          <li>Your private repos. We can't see them.</li>
          <li>Payment details. Starpull is free.</li>
        </ul>
        <p>We don't sell your data, show ads, run analytics or tracking, or use AI on your data.</p>
      </section>

      <section className="section">
        <h2>Who handles your data</h2>
        <ul>
          <li><strong>GitHub</strong> confirms who you are at sign-in and is where we read your public repos.</li>
          <li><strong>Supabase</strong> hosts our database, which holds everything under "What we store".</li>
          <li><strong>Render</strong> runs our server. Its logs, including the security log and IP addresses, are kept for 7 days.</li>
          <li><strong>Vercel</strong> serves this website and, like any web host, sees your IP address when you visit.</li>
          <li><strong>Have I Been Pwned</strong> checks new passwords against leaked ones. It receives only the first 5 characters of a scrambled (hashed) password.</li>
        </ul>
      </section>

      <section className="section">
        <h2>Cookies</h2>
        <p>
          One cookie keeps you logged in, and a short-lived one remembers your GitHub sign-in while you finish creating
          an account. Both are needed for the site to work. There are no tracking or advertising cookies, so there's no
          cookie banner.
        </p>
      </section>

      <section className="section">
        <h2>How it's protected</h2>
        <ul>
          <li>Every connection is encrypted, from your browser to our database.</li>
          <li>Your login is a cookie that scripts on the page can't read. It expires after a day and ends the moment you log out.</li>
          <li>New passwords need at least 12 characters with upper and lowercase letters and a symbol, can't contain your username or email name, and are checked against passwords leaked in known data breaches. For that check only the first 5 characters of a scrambled (hashed) version leave our server, never the password.</li>
          <li>Five wrong passwords lock the account for 15 minutes. Changing your email, password or deleting the account asks for your password again.</li>
          <li>Other sites can't make changes to your account on your behalf, and the site blocks scripts from anywhere but itself.</li>
          <li>Our security log records sign-ins and account changes, never passwords or login cookies.</li>
        </ul>
      </section>

      <section className="section">
        <h2>Your controls</h2>
        <p>
          In <Link to="/account">Account settings</Link> you can change your email or password, refresh your repos, sign out
          of every device, and delete your account. Deleting removes your account and everything listed under "What we store"
          immediately. Public information about open-source projects (issues, labels, stars) stays, because it isn't about you.
        </p>
        <p>
          Account data stays until you delete your account. IP addresses used against password guessing are deleted after
          an hour, and server logs after 7 days.
        </p>
        <p>
          GitHub keeps its own record that you approved Starpull, which is why signing in again skips GitHub's approval
          screen. Starpull can't remove it for you, because we don't keep your GitHub token. Revoke it yourself under{' '}
          <a href="https://github.com/settings/applications" target="_blank" rel="noreferrer">GitHub → Settings → Applications</a>.
        </p>
      </section>

      <section className="section">
        <h2>Age and contact</h2>
        <p>
          Starpull is for people 13 and older, the same minimum as GitHub. Questions about your data:{' '}
          <a href="https://github.com/JVP7/firstpr/issues/new" target="_blank" rel="noreferrer">open an issue on GitHub</a>.
          See also the <Link to="/terms">Terms of service</Link>.
        </p>
      </section>
    </article>
  )
}
