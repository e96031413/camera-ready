# Counterintuitive Principles for Academic Research

Consolidated from EvoScientist/EvoSkills research methodology. These principles apply across all phases.

## Research & Ideation

1. **Problem selection > solution design**: Spending 2 weeks finding the right problem beats spending 2 months engineering a solution to the wrong one. The best papers solve important problems with simple methods.

2. **Quantity before quality in idea generation**: Force yourself to generate 20+ ideas before evaluating any. Breakthrough ideas often emerge from forced variation, not from polishing your first idea.

3. **Narrow before broad**: "Improve transformers for long documents" will fail review. "Fix attention collapse in 100+ layer vision transformers for medical imaging" has a chance. Narrow claims are easier to prove and harder to reject.

4. **Write the rejection letter first**: Before writing your paper, write the review that would reject it. Every weakness you find now is one you can address before submission.

## Experiment Design

5. **Design ablations before writing method text**: If you can't design a clean ablation study for a component, the component shouldn't exist. Ablation-first thinking forces modular design.

6. **Initial implementation validates infrastructure, not ideas**: Stage 1 is about proving your pipeline works. Do not judge your method based on Stage 1 results.

7. **One variable per experiment**: Changing LR and batch size simultaneously makes results uninterpretable. The discipline of changing one variable is more important than running more experiments.

8. **Budget limits prevent rabbit holes**: A fixed attempt budget (e.g., ≤12 for tuning) forces you to be systematic rather than randomly trying things. When budget is exhausted, diagnose — don't retry.

9. **Failed attempts are data**: Log every failed experiment. The pattern of failures often reveals the actual problem better than any single success.

10. **Allocate compute to stress tests, not demos**: A paper with 3 impressive demos but no failure analysis will be rejected. A paper with modest results but thorough stress testing will be respected.

## Writing

11. **Underclaim in prose, overdeliver in evidence**: "Our method achieves modest improvements" + a table showing 5% gains across 3 datasets beats "Our revolutionary approach" + one cherry-picked result. Reviewers trust humble claims backed by strong evidence.

12. **Lead with mechanism, not motivation**: "We propose X because the existing landscape has gap Y" is weak. "X works by doing Z, which directly addresses the failure mode of Y" is strong. Show the mechanism first, then explain why it matters.

13. **One decisive figure beats five mediocre ones**: A single, well-designed pipeline figure that tells the complete story is worth more than five hastily-made plots. Invest 25% of your time on figures.

14. **Write the Abstract last**: The Abstract is a summary of your actual contributions, not a plan. Writing it first locks you into claims you haven't proven yet.

15. **Three sentences without a citation is a red flag**: In a review paper, every factual claim needs backing. In a methods paper, every claim about related work needs backing. Unsupported claims are the fastest way to get rejected.

## Review & Revision

16. **Reject-first simulation**: Before submitting, role-play as a hostile reviewer. What would you attack? Fix those weaknesses proactively.

17. **Delete one unsupported strong claim**: Every paper has at least one overclaim. Find it. If you can't support it, delete it. One deleted overclaim improves the entire paper's credibility.

18. **Score trust, not only gains**: Reviewers evaluate whether they believe your results, not just whether the numbers are good. Reproducibility details, error bars, and honest limitations build trust.

19. **Promote one explicit limitation**: Counter-intuitively, stating a clear limitation makes the paper stronger. It shows intellectual honesty and prevents reviewers from "discovering" it themselves.

20. **Attack your own novelty claim**: If you claim "first to do X", search exhaustively to verify. Being caught making a false novelty claim is paper-killing.

## Rebuttal & Response

21. **Submit rebuttal even with extreme scores**: Rebuttals change outcomes more often than you think. A score of 3/10 from one reviewer doesn't mean the paper is bad — it means that reviewer had specific concerns you can address.

22. **Concede small, win big**: Acknowledge minor weaknesses quickly ("The reviewer correctly notes..."). This builds credibility for your defense of major points.

23. **One new experiment beats paragraphs of explanation**: If a reviewer doubts your method works on dataset X, run the experiment. "We ran the suggested experiment and results confirm..." is the strongest possible response.

24. **Best rebuttal is written before submission (prebuttal)**: Anticipate likely reviewer concerns and address them in the paper. The goal is to make the rebuttal unnecessary.

## Memory & Learning

25. **Abstract before storing**: "LR=3e-4 worked" is useless. "ViT-B converges at LR~3e-4 with cosine schedule on ImageNet-scale data" is reusable across projects.

26. **Failed directions are as valuable as successful ones**: Knowing what NOT to do saves more time than knowing what to do. Always record why a direction failed.

27. **Distinguish implementation from fundamental failures**: A method that failed because of a bug is still viable. A method that failed because the core assumption is wrong should be abandoned. This is the single most important classification.

## How to Apply

These principles are NOT rules to follow blindly. They are heuristics that are correct more often than naive intuition suggests. When in doubt:

1. Check if the principle applies to your specific situation
2. If it conflicts with domain-specific knowledge, domain knowledge wins
3. If it conflicts with reviewer feedback, reviewer feedback wins
4. If two principles conflict, choose the one that reduces risk

The meta-principle: **Measure twice, cut once.** Think before acting. Plan before coding. Read before writing.
