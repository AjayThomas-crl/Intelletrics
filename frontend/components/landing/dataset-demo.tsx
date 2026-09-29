"use client";

import { useState } from "react";
import { ArrowUpRight, Check, FileSpreadsheet } from "lucide-react";
import styles from "@/app/landing.module.css";

const questions = [
  { question: "Which region leads?", answer: "East brings in $31,000.", detail: "That’s 43.1% of revenue across all six orders.", label: "Revenue by region", source: "region, revenue" },
  { question: "What’s the total revenue?", answer: "$72,000 across 6 orders.", detail: "The sum of every revenue value in the sample.", label: "Revenue by region", source: "revenue" },
  { question: "Average order value?", answer: "$12,000 per order.", detail: "$72,000 in revenue divided by 6 orders.", label: "Revenue by region", source: "revenue" },
];
const rows = [
  ["001", "East", "12,400"], ["002", "West", "8,600"], ["003", "East", "18,600"],
  ["004", "West", "11,200"], ["005", "North", "14,800"], ["006", "South", "6,400"],
];
const regions = [{ name: "East", value: 31000 }, { name: "West", value: 19800 }, { name: "North", value: 14800 }, { name: "South", value: 6400 }];

export function DatasetDemo() {
  const [active, setActive] = useState(0);
  const current = questions[active];
  return (
    <div className={styles.demo}>
      <div className={styles.demoToolbar}>
        <span><FileSpreadsheet size={16} aria-hidden="true" /> regional_sales.csv</span>
        <span className={styles.demoTag}>INTERACTIVE SAMPLE</span>
      </div>
      <div className={styles.demoGrid}>
        <div className={styles.dataPane}>
          <div className={styles.paneTitle}><span>THE DATA</span><span>6 ROWS · 3 COLUMNS</span></div>
          <table className={styles.sampleTable}>
            <caption className="sr-only">Six example sales orders, totaling 72,000 dollars</caption>
            <thead><tr><th scope="col">order</th><th scope="col">region</th><th scope="col">revenue ($)</th></tr></thead>
            <tbody>{rows.map(([id, region, revenue]) => <tr key={id}><td>{id}</td><td>{region}</td><td>{revenue}</td></tr>)}</tbody>
          </table>
          <div className={styles.dataFoot}><Check size={13} aria-hidden="true" /><span>No missing values in this sample</span></div>
        </div>
        <div className={styles.answerPane}>
          <div className={styles.paneTitle}><span>THE QUESTION</span><ArrowUpRight size={16} aria-hidden="true" /></div>
          <div className={styles.questionChoices} aria-label="Try a sample question">
            {questions.map(({ question }, index) => <button key={question} aria-pressed={active === index} onClick={() => setActive(index)}>{question}</button>)}
          </div>
          <div aria-live="polite" aria-atomic="true" className={styles.demoAnswer}>
            <h3>{current.answer}</h3><p>{current.detail}</p>
          </div>
          <div className={styles.demoChart} role="img" aria-label="Revenue by region: East 31,000, West 19,800, North 14,800, South 6,400 dollars">
            {regions.map(({ name, value }) => <div className={styles.chartRow} key={name}><span>{name}</span><div><i style={{ width: `${value / 31000 * 100}%` }} /></div><b>${(value / 1000).toFixed(1)}k</b></div>)}
          </div>
          <div className={styles.answerFoot}>SOURCE COLUMNS <span>{current.source}</span></div>
        </div>
      </div>
      <div className={styles.demoFooter}><span>A small example. Your own questions start with your own file.</span><span>PRECOMPUTED DEMO · NO AI CALLS</span></div>
    </div>
  );
}
