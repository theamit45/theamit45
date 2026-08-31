<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/header.svg" alt="Amit Kumar Maurya, AI Evaluation Specialist and Benchmark Engineer" />

<div align="center">

<a href="https://git.io/typing-svg">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=3000&pause=800&color=4169E1&center=true&vCenter=true&width=760&lines=LLM+Evaluation+Specialist+%40+Handshake+AI;Building+terminal+benchmarks+that+test+AI+agents;Project+Dynamo+%E2%80%A2+Terminal-Bench+%E2%80%A2+Docker;350%2B+DSA+problems+solved" alt="Typing SVG" />
</a>

<br/>

<img src="https://komarev.com/ghpvc/?username=theamit45&label=Profile%20Views&color=8A2BE2&style=for-the-badge" alt="profile views" />
<a href="https://github.com/theamit45?tab=followers"><img src="https://img.shields.io/github/followers/theamit45?label=Followers&style=for-the-badge&color=4169E1&labelColor=1a1b27" alt="followers" /></a>
<img src="https://img.shields.io/badge/Focus-AI%20Evaluation-00CED1?style=for-the-badge&labelColor=1a1b27" alt="focus" />

<br/><br/>

<img src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/terminal.svg" alt="A terminal session running a Terminal-Bench task: the oracle solution scores 1.0, the nop baseline scores 0.0, and the agent fails" />

</div>

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## About Me

I'm a Computer Science engineer working at the seam between AI systems and rigorous testing. My work is building the environments that decide whether an AI coding agent is actually any good: isolated Docker sandboxes with fixed resource limits, Pytest suites that grade an agent's output automatically, and validation passes that prove a task scores `1.0` when solved and `0.0` when untouched.

Most of what I do is adversarial in a useful way. I design tasks that look tractable and then find the reasoning step where a frontier model quietly falls over.

- **LLM Evaluation Specialist** at **Handshake AI**, contributing to Project Dynamo
- **Artificial Intelligence Engineer** at **AfterQuery Experts**
- **AI & Frontier Trainer** at **Outlier**, working on RLHF pipelines
- Solved **350+ DSA problems** across LeetCode, GeeksforGeeks, Coding Ninjas and CodeChef
- Secured **10th rank** in Chase The Code 2.0

```python
class AmitKumarMaurya:
    role      = "LLM Evaluation Specialist @ Handshake AI"
    education = "B.E. Computer Science, Chandigarh University"
    stack     = ["Python", "Bash", "C++", "JavaScript", "React", "Node.js"]
    tooling   = ["Docker", "Pytest", "Git", "Linux", "uv/uvx", "Ruff"]
    focus     = "AI benchmark engineering and LLM evaluation"
    motto     = "If it isn't tested, it doesn't work."
```

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Where I Work

| Role | Organisation | Period |
|---|---|---|
| LLM Evaluation Specialist | [Handshake AI](https://joinhandshake.com/ai/) · Freelance | Jun 2026 to Present |
| Artificial Intelligence Engineer | AfterQuery Experts · Freelance | Apr 2026 to Present |
| AI & Frontier Trainer | Outlier · Freelance | Nov 2024 to Present |
| AI Software Engineer | Xelron · Full-time | Sep 2025 to May 2026 |

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Project Dynamo

[Project Dynamo](https://project-dynamo.learn.joinhandshake.com/) is the coding and software engineering track of the **Handshake AI Fellowship**. The goal is to measure how well autonomous agents handle real terminal work rather than tidy code-generation prompts, and the tasks are scored against the **Terminal-Bench** benchmark.

What I build for it:

- **Command-line test environments** that require an agent to reason across multiple steps, not just emit a plausible-looking patch
- **Repository repair and debugging scenarios**, where something is genuinely broken and the fix depends on reading the failure correctly
- **Reproducible Docker images** with pinned dependencies, so a task grades identically on any machine
- **Pytest verification suites** plus Oracle and NOP validation passes, confirming a task scores `1.0` when solved and `0.0` when left untouched
- **Failure-mode analysis**, documenting exactly where a model's reasoning broke down so the benchmark gets harder in the right places

I've shipped **150+ tasks** in total, spanning security, low-level and embedded systems, scientific computing, data processing and ETL, machine learning infrastructure, formal reasoning, and systems administration.

Toolchain: `Docker` · `Python` · `Bash` · `Pytest` · `uv/uvx` · `TOML` · `Git` · `GitHub CLI` · `Ruff`

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Other Evaluation Work

**AfterQuery Experts.** Building and reviewing evaluation data for large language models, with an emphasis on containerised reproducibility and multi-step engineering problems.

**Outlier.** Contributing to RLHF pipelines by writing expert-level prompts and rating paired model outputs on structured rubrics. I design adversarial, reasoning-heavy prompts to stress-test robustness across edge cases and ambiguous inputs, and every claim I submit is backed by a specific diff line.

**Xelron (previous).** Built Harbor and Terminal-Bench sandbox challenges covering debugging, system administration and data processing. Also ran the Marlin evaluation workflow, reviewing AI-generated code changes line by line against the original codebase and comparing two model responses side by side across multiple turns.

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Tech Stack

<div align="center">

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/tech-stack.svg" alt="Tech stack. Languages: Python, C++, C, Java, JavaScript, Bash. Web and data: React, Node.js, Express, MongoDB, HTML5, CSS3. Evaluation toolchain: Docker, Linux, Git, GitHub, Pytest, VS Code." />

<br/>

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/focus.svg" alt="Also working with SQL, Ruff, TOML, uv and uvx, Zod and Cursor. AI and LLM systems: prompt engineering, LLM evaluation, Terminal-Bench, RLHF, failure-mode analysis, agent sandboxing, GPT-5 and Claude Sonnet." />

</div>

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Projects

**MediAI.** An AI health assistant built on the MERN stack that explains without ever diagnosing. Every model response is parsed against a Zod schema and then passed through a deterministic rules engine that can only ever raise urgency, never lower it. If the text contains a stroke sign, the safety floor rewrites the assessment to `emergency` regardless of what the model concluded. It runs end to end with no API key via deterministic fixtures, so the test suite works offline in CI.

**Travel Website.** A responsive web application for browsing destinations and booking trips, built with HTML, CSS and Node.js.

**Covid-19 Tracker.** Daily and weekly case statistics pulled from live API datasets and plotted on Google Maps, built with JavaScript, HTML and CSS.

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## DSA & Problem Solving

<div align="center">

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/dsa.svg" alt="350+ problems solved across LeetCode, GeeksforGeeks, CodeChef and Coding Ninjas, with a LeetCode breakdown of 48 easy, 32 medium and 3 hard" />

</div>

The LeetCode numbers are pulled live from LeetCode's API by [`scripts/generate_cards.py`](scripts/generate_cards.py), so the ring and the bars move on their own as I solve more.

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## GitHub Stats

<div align="center">

<img height="195" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/github-stats.svg" alt="GitHub overview" />
<img height="195" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/top-languages.svg" alt="Most used languages" />

</div>

These cards are generated from the GitHub API by [`scripts/generate_cards.py`](scripts/generate_cards.py) and committed to this repository, so they include private repositories and never depend on a third-party service staying up.

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Contribution Graph

<div align="center">

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/contributions.svg" alt="Contribution heatmap for 2023 showing 1,281 contributions, with a peak of 11 in a single day" />

</div>

This heatmap is built straight from the GitHub contributions API by [`scripts/generate_cards.py`](scripts/generate_cards.py) and committed here, so it stays accurate regardless of what the profile page decides to display.

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Achievements & Certifications

| | |
|---|---|
| **10th Rank** | Chase The Code 2.0 |
| **350+ Problems** | Data Structures & Algorithms across four platforms |
| **150+ Tasks** | Shipped for Project Dynamo against the Terminal-Bench benchmark |
| **Elite Certificate** | Discrete Mathematics, NPTEL, IIT Madras |
| **Silver Certificate** | Programming in Java, NPTEL, IIT Kharagpur |
| **Silver Certificate** | Introduction to IoT, NPTEL, IIT Kharagpur |

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Education

**Bachelor of Engineering, Computer Science and Engineering** · 2021 to 2025
Chandigarh University, Gharuan, Punjab · CGPA 7.93

Relevant coursework: Data Structures & Algorithms, Operating Systems, Object Oriented Programming, Database Management Systems

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/divider.svg" alt="" />

## Connect With Me

<div align="center">

<a href="https://www.linkedin.com/in/amit-kumar-maurya-a2a244235/">
  <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" />
</a>
<a href="mailto:amitmaurya7071@gmail.com">
  <img src="https://img.shields.io/badge/Email-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Email" />
</a>
<a href="https://leetcode.com/u/theamit45/">
  <img src="https://img.shields.io/badge/LeetCode-FFA116?style=for-the-badge&logo=leetcode&logoColor=black" alt="LeetCode" />
</a>
<a href="https://github.com/theamit45">
  <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
</a>

<br/><br/>

<i>Open to conversations about AI evaluation, benchmark engineering, and backend systems.</i>

</div>

<img width="100%" src="https://raw.githubusercontent.com/theamit45/theamit45/main/assets/footer.svg" alt="If it isn't tested, it doesn't work. amitmaurya7071@gmail.com and linkedin.com/in/amit-kumar-maurya" />
