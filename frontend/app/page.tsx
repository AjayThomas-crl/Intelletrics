import Link from "next/link";
import Image from "next/image";
import { ArrowDown, ArrowRight, ArrowUpRight } from "lucide-react";
import { DatasetDemo } from "@/components/landing/dataset-demo";
import styles from "./landing.module.css";

const workflow = [
  { number: "01", title: "Bring the spreadsheet.", text: "Upload a CSV or Excel file. Your columns, rows, and a preview are ready to inspect in one workspace.", note: ".CSV / .XLSX / .XLS" },
  { number: "02", title: "Get your bearings.", text: "See distributions, summary statistics, and missing values before you start drawing conclusions.", note: "PROFILE / CHARTS / DATA QUALITY" },
  { number: "03", title: "Ask a better question.", text: "Compare regions. Find a trend. Calculate a percentage. Ask in plain language and get the computed results alongside the source columns.", note: "FILTER / COMPARE / EXPLORE" },
];
const faqs = [
  { question: "What can I ask about my data?", answer: "Ask for totals, averages, filtered records, group comparisons, rankings, date trends, missing values, and statistical relationships. Be specific about columns and time periods. If a question needs information that isn’t in your file, Intelletrics will ask for clarification." },
  { question: "What files can I upload?", answer: "CSV and Excel files up to 25 MB, with up to 250,000 rows and 200 columns. Use a single header row and consistent formats. For Excel workbooks, the first worksheet is analyzed." },
  { question: "Where do the answers come from?", answer: "AI translates your question into a read-only query. The calculation runs on your uploaded dataset, and the resulting values are shown directly. Column names, types, and a small number of sample text values may be sent to the AI provider to help it understand your question." },
  { question: "Is this an open-source project?", answer: "Yes. Intelletrics is built by Ajay Thomas and released under the MIT license. You can inspect the code, contribute, or run it yourself." },
];

export default function Home() {
  return (
    <div className={styles.landing}>
      <a className={styles.skipLink} href="#content">Skip to content</a>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="Intelletrics home"><Image src="/icon.svg" alt="" width={29} height={29} />intelletrics<span className={styles.brandPeriod}>.</span></Link>
        <nav aria-label="Main navigation" className={styles.nav}>
          <a href="#how-it-works" className={styles.navAbout}>How it works</a>
          <Link href="/auth/login">Sign in</Link>
          <Link href="/auth/signup" className={styles.navCta}>Open workspace <ArrowUpRight size={15} aria-hidden="true" /></Link>
        </nav>
      </header>

      <section className={styles.hero} id="content">
        <div className={styles.heroEyebrow}><span className={styles.smallSquare} /> A LITTLE CLARITY GOES A LONG WAY.</div>
        <div className={styles.heroGrid}>
          <h1>The answer’s in<br />your <em>spreadsheet.</em></h1>
          <div className={styles.heroAside}>
            <span className={styles.asideIndex}>[ DATA → UNDERSTANDING ]</span>
            <p>Bring the file. See the patterns.<br />Ask the next question.</p>
            <p className={styles.heroDescription}>A focused workspace for exploring CSV and Excel files, with charts, statistics, and answers grounded in your data.</p>
            <Link href="/auth/signup" className={styles.primaryLink}>Get started <ArrowUpRight size={18} aria-hidden="true" /></Link>
            <span className={styles.heroFine}>No code or SQL needed.</span>
          </div>
        </div>
        <div className={styles.heroBottom}><span>BUILT FOR THE “WAIT, WHAT IF?” MOMENT.</span><a href="#try-it">Take a closer look <ArrowDown size={14} aria-hidden="true" /></a></div>
      </section>

      <section id="try-it" className={styles.demoSection} aria-labelledby="demo-heading">
        <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>A FILE. A QUESTION. AN ANSWER.</span><h2 id="demo-heading">Here’s what that looks like.</h2></div><p>Start with a small sales file.<br />Pick a question and see what turns up.</p></div>
        <DatasetDemo />
      </section>

      <section id="how-it-works" className={styles.workflowSection} aria-labelledby="workflow-heading">
        <div className={styles.workflowIntro}><span className={styles.eyebrow}>FROM FIRST LOOK TO FOLLOW-UP</span><h2 id="workflow-heading">Less fiddling.<br /><em>More finding out.</em></h2><p>All the useful parts of exploring a dataset, in one place.</p><Link href="/auth/signup" className={styles.underlinedLink}>Try it with your file <ArrowRight size={16} aria-hidden="true" /></Link></div>
        <div className={styles.workflowList}>{workflow.map((step) => <article key={step.number} className={styles.workflowRow}><span className={styles.stepNumber}>{step.number}</span><div><h3>{step.title}</h3><p>{step.text}</p><span className={styles.stepNote}>{step.note}</span></div></article>)}</div>
      </section>

      <section className={styles.manifesto}>
        <span className={styles.eyebrow}>BUILT WITH A SIMPLE IDEA</span>
        <p>You shouldn’t need a whole<br className={styles.desktopBreak} /> afternoon to understand<br className={styles.desktopBreak} /> <em>one spreadsheet.</em></p>
        <div><span>Intelletrics is an independent, open-source project.<br />Built by Ajay Thomas. Made for curious people.</span><a href="https://github.com/AjayThomas-crl/Intelletrics" target="_blank" rel="noreferrer">Look under the hood <ArrowUpRight size={15} aria-hidden="true" /></a></div>
      </section>

      <section className={styles.faqSection} aria-labelledby="faq-heading"><div><span className={styles.eyebrow}>A FEW THINGS TO KNOW</span><h2 id="faq-heading">Before you<br /><em>jump in.</em></h2></div><div className={styles.faqList}>{faqs.map((faq) => <details key={faq.question}><summary>{faq.question}<span aria-hidden="true">+</span></summary><p>{faq.answer}</p></details>)}</div></section>

      <section className={styles.closing}><div><span className={styles.eyebrow}>YOUR FILE. YOUR NEXT QUESTION.</span><h2>Let’s see what’s in there.</h2></div><Link href="/auth/signup" className={styles.primaryLink}>Open your workspace <ArrowUpRight size={20} aria-hidden="true" /></Link></section>
      <footer className={styles.footer}><Link href="/" className={styles.brand}><Image src="/icon.svg" alt="" width={23} height={23} />intelletrics.</Link><span>© {new Date().getFullYear()} · Made by Ajay Thomas</span><a href="https://github.com/AjayThomas-crl/Intelletrics" target="_blank" rel="noreferrer">Open source <ArrowUpRight size={13} aria-hidden="true" /></a></footer>
    </div>
  );
}
