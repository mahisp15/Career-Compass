import { useEffect, useMemo, useState } from "react";
import { api, API_BASE_URL } from "./services/api";
import "./App.css";

const asArray = (value) => (Array.isArray(value) ? value : value?.items || value?.data || []);
const labelOf = (item) => (typeof item === "string" ? item : item?.name || item?.title || item?.role || item?.company_name || item?.company || item?.skill || item?.label || "—");
const formatLabel = (key) => key.replace(/[_-]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const formatValue = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map((item) => (typeof item === "object" ? labelOf(item) : item)).join(", ") : "—";
  if (typeof value === "object") return labelOf(value);
  return String(value);
};

function App() {
  const [skills, setSkills] = useState([]);
  const [roles, setRoles] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [trends, setTrends] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [targetRole, setTargetRole] = useState("");
  const [targetCompany, setTargetCompany] = useState("");
  const [salaryExpectation, setSalaryExpectation] = useState("");
  const [skillSearch, setSkillSearch] = useState("");
  const [trendFilter, setTrendFilter] = useState("All");
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [analysisError, setAnalysisError] = useState("");

  useEffect(() => {
    Promise.all([api.getSkills(), api.getRoles(), api.getCompanies(), api.getTrends(), api.getModelMetrics().catch(() => null)])
      .then(([skillData, roleData, companyData, trendData, metricData]) => {
        setSkills(asArray(skillData)); setRoles(asArray(roleData)); setCompanies(asArray(companyData)); setTrends(asArray(trendData)); setMetrics(metricData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const trendMap = useMemo(() => Object.fromEntries(trends.map((item) => [item.skill || item.name, item])), [trends]);
  const filteredSkills = useMemo(() => skills.filter((item) => {
    const name = labelOf(item);
    const trend = trendMap[name]?.trend;
    return name.toLowerCase().includes(skillSearch.toLowerCase()) && (trendFilter === "All" || trend === trendFilter);
  }).sort((a, b) => Number(a.demand_rank ?? 9999) - Number(b.demand_rank ?? 9999)), [skills, skillSearch, trendFilter, trendMap]);
  const trendCounts = useMemo(() => ({ Rising: trends.filter((item) => item.trend === "Rising").length, Stable: trends.filter((item) => item.trend === "Stable").length, Declining: trends.filter((item) => item.trend === "Declining").length }), [trends]);
  const topSkills = useMemo(() => [...skills].sort((a, b) => Number(b.posting_count || 0) - Number(a.posting_count || 0)).slice(0, 6), [skills]);

  const toggleSkill = (name) => setSelectedSkills((current) => current.includes(name) ? current.filter((skill) => skill !== name) : [...current, name]);
  const handleAnalyze = async (event) => {
    event.preventDefault(); setAnalyzing(true); setAnalysisError(""); setAnalysis(null);
    try {
      const result = await api.analyze({ skills: selectedSkills, target_role: targetRole, target_company: targetCompany, salary_expectation: Number(salaryExpectation) });
      setAnalysis(result); document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) { setAnalysisError(err.message); } finally { setAnalyzing(false); }
  };
  const handleSkillDetails = async (name) => {
    try { setSelectedSkill(await api.getSkill(name)); } catch (err) { setError(err.message); }
  };

  if (loading) return <div className="center-page"><div className="loader"><span className="brand-mark">CC</span><h2>Loading Career Compass</h2><p>Connecting to live career intelligence...</p></div></div>;
  if (error && !skills.length) return <div className="center-page"><div className="error-card"><span className="alert-icon">!</span><h2>Backend connection required</h2><p>{error}</p><code>{API_BASE_URL}</code><p className="muted">Start the FastAPI server and refresh this page. No sample data is used.</p></div></div>;

  return <div className="app-shell">
    <header className="topbar"><div className="topbar-inner"><a className="brand" href="#top"><span className="brand-mark">CC</span><span><strong>Career Compass</strong><small>ML-powered career intelligence</small></span></a><nav><a href="#analyze">Analyze</a><a href="#explorer">Skill Explorer</a><a href="#results">Results</a></nav><span className="live-pill"><i /> Live API</span></div></header>
    <main id="top">
      <section className="hero"><div className="hero-copy"><span className="eyebrow">CAREER INTELLIGENCE PLATFORM</span><h1>Make your next<br /><em>move</em> count.</h1><p>Turn your current skills into a data-backed career path. Compare your profile with real market demand, salary signals, and target companies.</p><div className="hero-meta"><span><b>{skills.length || "—"}</b> skills tracked</span><span><b>{roles.length || "—"}</b> roles available</span><span><b>{companies.length || "—"}</b> companies indexed</span></div></div><div className="hero-orbit"><div className="orbit orbit-a" /><div className="orbit orbit-b" /><div className="orbit-center"><span>CC</span><small>YOUR<br />CAREER<br />SIGNAL</small></div><div className="orbit-tag tag-one">Skills</div><div className="orbit-tag tag-two">Market</div><div className="orbit-tag tag-three">Growth</div></div></section>
      <section id="analyze" className="panel analyze-panel"><div className="section-intro"><div><span className="eyebrow">01 / PERSONALIZE</span><h2>Map your career direction</h2><p>Tell us where you are headed. Every option below is loaded from the live FastAPI backend.</p></div><span className="step-chip">Takes ~ 30 seconds</span></div>
        <form onSubmit={handleAnalyze} className="analysis-form"><div className="field full"><label>Current skills <span>Choose all that apply</span></label><div className="skill-picker"><div className="picker-search"><span>⌕</span><input value={skillSearch} onChange={(e) => setSkillSearch(e.target.value)} placeholder="Search the skills you use today..." /></div><div className="selected-tags">{selectedSkills.map((skill) => <button type="button" key={skill} onClick={() => toggleSkill(skill)} className="tag selected">{skill} <span>×</span></button>)}{!selectedSkills.length && <span className="placeholder">No skills selected yet</span>}</div><div className="skill-options">{skills.filter((skill) => labelOf(skill).toLowerCase().includes(skillSearch.toLowerCase())).slice(0, 18).map((skill) => { const name = labelOf(skill); return <button type="button" key={name} onClick={() => toggleSkill(name)} className={`skill-option ${selectedSkills.includes(name) ? "chosen" : ""}`}><span>{selectedSkills.includes(name) ? "✓" : "+"}</span>{name}</button>; })}</div></div></div><div className="field"><label htmlFor="role">Target role</label><select id="role" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} required><option value="">Select a role</option>{roles.map((role) => <option key={labelOf(role)} value={labelOf(role)}>{labelOf(role)}</option>)}</select></div><div className="field"><label htmlFor="company">Dream company</label><select id="company" value={targetCompany} onChange={(e) => setTargetCompany(e.target.value)} required><option value="">Select a company</option>{companies.map((company) => <option key={labelOf(company)} value={labelOf(company)}>{labelOf(company)}</option>)}</select></div><div className="field"><label htmlFor="salary">Salary expectation <span>Annual</span></label><div className="input-prefix"><b>$</b><input id="salary" type="number" min="0" value={salaryExpectation} onChange={(e) => setSalaryExpectation(e.target.value)} placeholder="e.g. 95000" required /></div></div><div className="form-action"><button className="primary-button" disabled={analyzing || !selectedSkills.length}>{analyzing ? "Analyzing your profile..." : "Analyze My Career  →"}</button>{!selectedSkills.length && <small>Select at least one skill to continue</small>}</div></form>{analysisError && <div className="inline-error">{analysisError}</div>}</section>
      {analysis && <Results analysis={analysis} metrics={metrics} />}
      {!analysis && <section className="signal-strip"><div><span className="eyebrow">MARKET PULSE</span><h2>See what the market is rewarding.</h2></div><div className="pulse-stats"><Stat value={trendCounts.Rising} label="Rising skills" tone="green" /><Stat value={trendCounts.Stable} label="Stable skills" tone="blue" /><Stat value={trendCounts.Declining} label="Declining skills" tone="orange" /></div></section>}
      <section id="explorer" className="explorer-section"><div className="section-intro"><div><span className="eyebrow">02 / EXPLORE</span><h2>Skill Explorer</h2><p>Search the dataset and inspect the signals behind every skill.</p></div><span className="count-badge">{skills.length} skills</span></div><div className="top-skill-grid">{topSkills.map((skill) => <button key={labelOf(skill)} className="top-skill" onClick={() => handleSkillDetails(labelOf(skill))}><span className="rank">#{skill.demand_rank ?? "—"}</span><strong>{labelOf(skill)}</strong><span>{formatValue(skill.posting_count)} postings <b>↗</b></span></button>)}</div><div className="explorer-toolbar"><div className="search-control"><span>⌕</span><input value={skillSearch} onChange={(e) => setSkillSearch(e.target.value)} placeholder="Search all skills..." /></div><div className="filter-group"><span>Trend</span>{["All", "Rising", "Stable", "Declining"].map((filter) => <button key={filter} className={trendFilter === filter ? "active" : ""} onClick={() => setTrendFilter(filter)}>{filter}</button>)}</div></div><div className="table-card"><table><thead><tr><th>Rank</th><th>Skill</th><th>Postings</th><th>Avg. salary</th><th>Demand share</th><th>Trend</th><th /></tr></thead><tbody>{filteredSkills.map((skill) => { const name = labelOf(skill); const trend = trendMap[name]?.trend; return <tr key={name} onClick={() => handleSkillDetails(name)}><td className="rank-cell">#{skill.demand_rank ?? "—"}</td><td><strong>{name}</strong></td><td>{formatValue(skill.posting_count)}</td><td>{skill.avg_salary != null ? `$${Math.round(skill.avg_salary).toLocaleString()}` : "—"}</td><td>{skill.demand_share_pct != null ? `${Number(skill.demand_share_pct).toFixed(1)}%` : "—"}</td><td><TrendBadge trend={trend} /></td><td className="arrow">→</td></tr>; })}</tbody></table>{!filteredSkills.length && <div className="empty-state">No skills match the current search or trend filter.</div>}</div></section>
    </main><footer><span>Career Compass</span><span>Live data from FastAPI · No mock business data</span></footer>{selectedSkill && <SkillDetail skill={selectedSkill} onClose={() => setSelectedSkill(null)} />}
  </div>;
}

function findValue(source, keys) {
  if (!source || typeof source !== "object") return undefined;
  for (const key of keys) if (source[key] !== undefined && source[key] !== null) return source[key];
  for (const container of ["data", "result", "analysis", "summary", "details", "metrics"]) {
    if (source[container] && typeof source[container] === "object") {
      for (const key of keys) if (source[container][key] !== undefined && source[container][key] !== null) return source[container][key];
    }
  }
  return undefined;
}

function SkillDetail({ skill, onClose }) {
  const demand = skill?.demand || skill;
  const trend = skill?.trend || {};
  return <div className="modal-backdrop" onClick={onClose}><div className="detail-modal" onClick={(event) => event.stopPropagation()}><button className="close-button" onClick={onClose}>×</button><span className="eyebrow">SKILL DETAIL</span><h2>{labelOf(skill)}</h2><p className="muted">Live fields returned by <code>/api/skills/{labelOf(skill)}</code></p><div className="detail-grid"><Detail label="Posting count" value={demand.posting_count} /><Detail label="Average salary" value={demand.avg_salary != null ? money(demand.avg_salary) : null} /><Detail label="Demand score" value={demand.avg_demand_score} /><Detail label="Demand share" value={demand.demand_share_pct != null ? `${demand.demand_share_pct}%` : null} /><Detail label="Demand rank" value={demand.demand_rank} /><Detail label="Trend" value={trend.trend} /><Detail label="Trend slope" value={trend.trend_slope} /><Detail label="Percentage change" value={trend.percentage_change != null ? `${trend.percentage_change}%` : null} /></div></div></div>;
}

function findSection(analysis, keys, fallback = undefined) {
  const value = findValue(analysis, keys);
  return value === undefined ? fallback : value;
}

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = Number(value);
  return Number.isNaN(numeric) ? `${value} USD` : `$${Math.round(numeric).toLocaleString()} USD`;
}

function numberText(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = Number(value);
  return Number.isNaN(numeric) ? `${value}${suffix}` : `${numeric.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

function percentage(value) {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = Number(value);
  return Number.isNaN(numeric) ? String(value) : `${(numeric <= 1 ? numeric * 100 : numeric).toFixed(1)}%`;
}

function listValue(value) {
  if (Array.isArray(value)) return value.map((item) => typeof item === "object" ? labelOf(item) : String(item)).filter(Boolean);
  if (typeof value === "string") return value.split(/[,|]/).map((item) => item.trim()).filter(Boolean);
  return [];
}

function readableReasons(item) {
  const reasons = listValue(findValue(item, ["reasons", "explanations", "explanation", "why_recommended", "recommendation_reasons"]));
  if (reasons.length) return reasons;
  const fallback = [];
  const trend = findValue(item, ["trend", "trend_label"]);
  const postings = findValue(item, ["posting_count", "postings", "total_postings"]);
  const demandScore = findValue(item, ["demand_score", "avg_demand_score"]);
  if (trend) fallback.push(`${formatLabel(String(trend))} trend`);
  if (postings !== undefined) fallback.push(`Appears in ${numberText(postings)} postings`);
  if (demandScore !== undefined) fallback.push(`Demand score: ${numberText(demandScore)}`);
  return fallback;
}

function Results({ analysis, metrics }) {
  const careerSummary = findSection(analysis, ["career_summary"], {});
  const skillGapAnalysis = findSection(analysis, ["skill_gap_analysis"], {});
  const skillGaps = asArray(findValue(skillGapAnalysis, ["recommendations"]));
  const companyRecommendations = asArray(findSection(analysis, ["company_recommendations", "recommended_companies", "company_matches"], []));
  const roleRecommendations = asArray(findSection(analysis, ["role_recommendations", "recommended_roles", "role_matches"], []));
  const salary = findSection(analysis, ["salary_analysis"], {});
  const targetCompany = findSection(analysis, ["target_company_trend"], {});
  const trends = findSection(analysis, ["skill_trends", "skill_trends_summary", "trend_summary", "trends"], {});
  const renderedKnown = skillGaps.length || companyRecommendations.length || roleRecommendations.length || Object.keys(salary || {}).length || Object.keys(targetCompany || {}).length || Object.keys(trends || {}).length || Object.keys(careerSummary || {}).length;

  return <section id="results" className="results-section">
    <div className="section-intro"><div><span className="eyebrow">03 / YOUR READOUT</span><h2>Career analysis</h2><p>These insights are generated from the response returned by your backend.</p></div><span className="result-chip">Analysis complete</span></div>
    {Object.keys(careerSummary || {}).length > 0 && <SummaryCard value={careerSummary} />}
    <div className="results-block"><div className="results-block-title"><span className="eyebrow">SKILL GAP ANALYSIS</span><h3>Skills to prioritize next</h3></div>{skillGaps.length ? <div className="recommendation-grid">{skillGaps.map((item, index) => <SkillRecommendation key={`${labelOf(item)}-${index}`} item={item} />)}</div> : <EmptyResult text="No skill-gap recommendations were returned." />}</div>
    <div className="results-block"><div className="results-block-title"><span className="eyebrow">SALARY ANALYSIS</span><h3>Your market position</h3></div><SalaryCard value={salary} expectation={findSection(analysis, ["salary_expectation", "expected_salary", "user_salary_expectation"])} /></div>
    <div className="results-block"><div className="results-block-title"><span className="eyebrow">TARGET COMPANY TREND</span><h3>Company signal</h3></div><TargetCompanyCard value={targetCompany} fallbackName={findSection(analysis, ["target_company_name"])} /></div>
    <div className="results-block"><div className="results-block-title"><span className="eyebrow">COMPANY RECOMMENDATIONS</span><h3>Where your profile can travel</h3></div>{companyRecommendations.length ? <div className="recommendation-grid">{companyRecommendations.map((item, index) => <CompanyRecommendation key={`${labelOf(item)}-${index}`} item={item} />)}</div> : <EmptyResult text="No company recommendations were returned." />}</div>
    <div className="results-block"><div className="results-block-title"><span className="eyebrow">ROLE RECOMMENDATIONS</span><h3>Roles matching your direction</h3></div>{roleRecommendations.length ? <div className="recommendation-grid">{roleRecommendations.map((item, index) => <RoleRecommendation key={`${labelOf(item)}-${index}`} item={item} />)}</div> : <EmptyResult text="No role recommendations were returned." />}</div>
    <div className="results-block"><div className="results-block-title"><span className="eyebrow">SKILL TRENDS SUMMARY</span><h3>Market movement</h3></div><TrendSummary value={trends} /></div>
    {metrics && <div className="results-block"><div className="results-block-title"><span className="eyebrow">MODEL METRICS</span><h3>Prediction model performance</h3></div><MetricsCard value={metrics} /></div>}
    {!renderedKnown && <EmptyResult text="The backend returned no displayable analysis sections." />}
  </section>;
}

function SummaryCard({ value }) { const skills = listValue(value?.input_skills); return <div className="summary-card"><span className="result-icon">✦</span><div><span className="eyebrow">CAREER SUMMARY</span><div className="summary-fields"><Detail label="Skills" value={skills.length ? skills.join(", ") : "—"} /><Detail label="Target role" value={value?.target_role} /><Detail label="Target company" value={value?.target_company} /><Detail label="Salary expectation" value={money(value?.salary_expectation)} /></div></div></div>; }
function SkillRecommendation({ item }) { const skill = labelOf(item); const reasons = readableReasons(item); return <article className="structured-card skill-recommendation"><div className="card-title-row"><div><span className="card-kicker">RECOMMENDED SKILL</span><h4>{skill}</h4></div><span className="priority-badge">Priority: {numberText(item.priority_score)}</span></div><div className="metric-row"><Detail label="Trend" value={<TrendBadge trend={item.trend} />} /><Detail label="Trend slope" value={numberText(item.trend_slope)} /><Detail label="Postings" value={numberText(item.posting_count)} /><Detail label="Demand share" value={percentage(item.demand_share_pct)} /><Detail label="Demand score" value={numberText(item.avg_demand_score)} /><Detail label="Demand growth" value={numberText(item.avg_demand_growth)} /><Detail label="Average salary" value={money(item.avg_salary)} /><Detail label="Role relevant" value={item.role_relevant === undefined ? undefined : item.role_relevant ? "Yes" : "No"} /></div>{reasons.length > 0 && <div className="reasons"><strong>Why recommended</strong><ul>{reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>}</article>; }
function SalaryCard({ value }) { const band = value?.salary_band || {}; return <div className="salary-card"><SalaryMetric label="Your expectation" value={money(value?.user_expectation)} /><SalaryMetric label="Predicted salary" value={money(value?.predicted_salary)} accent /><SalaryMetric label="Salary range" value={`${money(band.low)} – ${money(band.high)}`} /><SalaryMetric label="Difference" value={money(value?.difference)} /><SalaryMetric label="Model info" value={displayField(value?.model_info)} /></div>; }
function SalaryMetric({ label, value, accent }) { return <div className={`salary-metric ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong></div>; }
function CompanyRecommendation({ item }) { const skills = listValue(findValue(item, ["top_skills", "skills", "matching_skills"])); const roles = listValue(findValue(item, ["top_roles", "roles", "matching_roles"])); return <article className="structured-card"><div className="card-title-row"><div><span className="card-kicker">COMPANY</span><h4>{labelOf(item)}</h4></div><span className="score-badge">{percentage(findValue(item, ["combined_score", "score"]))}</span></div><div className="metric-row compact"><Detail label="Skill match" value={percentage(findValue(item, ["skill_match", "skill_match_pct", "match_score"]))} /><Detail label="Similarity" value={numberText(findValue(item, ["similarity_score", "similarity"]))} /><Detail label="Combined" value={numberText(findValue(item, ["combined_score", "score"]))} /><Detail label="Hiring trend" value={findValue(item, ["hiring_trend", "trend"])} /><Detail label="Layoffs" value={findValue(item, ["layoffs", "layoff_status"])} /><Detail label="Review score" value={numberText(findValue(item, ["average_review_score", "avg_review_score", "review_score"]))} /></div><ChipList label="Top skills" values={skills} /><ChipList label="Top roles" values={roles} /><div className="company-footer"><span>Total postings</span><strong>{numberText(findValue(item, ["total_postings", "posting_count", "postings"]))}</strong></div><p className="explanation">{findValue(item, ["explanation", "explanations", "reason", "why_recommended"]) || "Recommendation based on the returned company signals."}</p></article>; }
function TargetCompanyCard({ value }) { const source = value && typeof value === "object" ? value : {}; const company = source.company; const companyName = typeof company === "object" ? labelOf(company) : company || "Target company"; const monthly = source.posting_volume_monthly; const recentTrend = source.recent_posting_trend === "unknown" ? "Insufficient data" : source.recent_posting_trend; return <article className="target-company-card"><div className="card-title-row"><div><span className="card-kicker">TARGET COMPANY</span><h4>{companyName}</h4></div><TrendBadge trend={recentTrend} tone={source.recent_posting_trend === "unknown" ? "unknown" : undefined} /></div><div className="target-company-grid"><Detail label="Job postings available" value={displayField(source.has_job_postings)} /><Detail label="Total postings" value={numberText(source.posting_volume_total)} /><Detail label="Layoffs" value={displayField(source.has_layoffs)} /><Detail label="Layoff events" value={displayField(source.layoff_events)} /><Detail label="Reviews" value={displayField(source.has_reviews)} /><Detail label="Review summary" value={displayField(source.review_summary)} /><Detail label="Average review score" value={displayField(source.review_summary?.average_review_score ?? source.review_summary?.avg_review_score)} /></div>{monthly !== undefined && <div className="monthly-activity"><strong>Monthly posting activity</strong><div className="activity-text">{displayField(monthly)}</div></div>}<div className="company-signal-note"><span>Layoff summary</span>{displayField(source.layoff_summary)}</div></article>; }
function RoleRecommendation({ item }) { return <article className="structured-card"><div className="card-title-row"><div><span className="card-kicker">ROLE</span><h4>{labelOf(item)}</h4><span className="role-category">{findValue(item, ["category", "role_category"]) || "Career match"}</span></div><span className="score-badge">Match: {percentage(findValue(item, ["match_score", "score", "match_percentage"]))}</span></div><ChipList label="Matching skills" values={listValue(findValue(item, ["matching_skills", "matched_skills", "skills_match"]))} /><ChipList label="Missing skills" values={listValue(findValue(item, ["missing_skills", "skill_gaps", "gaps"]))} /></article>; }
function ChipList({ label, values }) { if (!values.length) return null; return <div className="chip-list"><span>{label}</span><div>{values.map((value, index) => <b key={`${value}-${index}`}>{value}</b>)}</div></div>; }
function TrendSummary({ value }) { const source = value && typeof value === "object" ? value : {}; return <div className="trend-summary"><TrendCount label="Rising" value={findValue(source, ["rising", "Rising", "rising_count"])} tone="rising" /><TrendCount label="Stable" value={findValue(source, ["stable", "Stable", "stable_count"])} tone="stable" /><TrendCount label="Declining" value={findValue(source, ["declining", "Declining", "declining_count"])} tone="declining" /></div>; }
function TrendCount({ label, value, tone }) { return <div className={`trend-count ${tone}`}><span>{label}</span><strong>{numberText(value)}</strong><TrendBadge trend={label} /></div>; }
function MetricsCard({ value }) { const source = value?.metrics || {}; return <div className="metrics-card structured-metrics"><div className="metrics-grid"><Detail label="Model" value={value?.model_type} /><Detail label="Test MAE" value={numberText(source.test_MAE)} /><Detail label="Test RMSE" value={numberText(source.test_RMSE)} /><Detail label="Test R²" value={numberText(source.test_R2)} /><Detail label="Cross-validation MAE" value={numberText(source.cv_MAE)} /><Detail label="CV MAE std" value={numberText(source.cv_MAE_std)} /></div><p className="metrics-note">Model performance is based on the available dataset. The dataset has limited salary variation, so these metrics may not represent real-world performance.</p></div>; }
function EmptyResult({ text }) { return <div className="empty-result">{text}</div>; }
function displayField(value) { if (value === undefined || value === null || value === "") return "—"; if (Array.isArray(value)) return value.map((item) => typeof item === "object" ? labelOf(item) : String(item)).join(", ") || "—"; if (typeof value === "object") return findValue(value, ["name", "company_name", "summary", "status", "value", "count", "score"]) ?? labelOf(value); return String(value); }
function Detail({ label, value }) { return <div className="detail-stat"><span>{label}</span><strong>{displayField(value)}</strong></div>; }
function TrendBadge({ trend, tone }) { return <span className={`trend-badge ${(tone || trend || "unknown").toString().toLowerCase()}`}>{trend || "Unknown"}</span>; }
function Stat({ value, label, tone }) { return <div className="pulse-stat"><span className={`pulse-dot ${tone}`} /><strong>{value}</strong><span>{label}</span></div>; }

export default App;
