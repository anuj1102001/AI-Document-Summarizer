# Hybrid Work and Team Output: A Twelve-Month Field Study in Three Software Firms

SYNTHETIC DOCUMENT written for evaluating Margin. The study, firms, authors and results are fictional.

Abstract

We followed 412 software engineers across three firms in Hyderabad for twelve months as they moved from fully on-site work to one of two hybrid schedules: two fixed office days per week, or flexible office days chosen by each team. We measured merged pull requests, code-review turnaround, self-reported focus time and voluntary attrition. Teams on fixed office days merged 4.1% more pull requests than their on-site baseline, while teams with flexible days showed no significant change. Review turnaround improved by 18% under fixed days. Voluntary attrition fell from 14.2% to 9.6% across both hybrid groups. We find that coordination, not location itself, explains most of the difference.

1. Introduction

Debates about remote and hybrid work often compare averages across companies with very different practices. Our design instead follows the same engineers before and after a policy change, which controls for individual ability and for most team-level differences. We ask three questions: whether hybrid schedules change output, whether they change collaboration speed, and whether they change retention.

\f

2. Method

2.1 Participants

Participants were 412 engineers (31% women) from 58 teams at three mid-sized software firms, referred to as Firm A (payments), Firm B (logistics) and Firm C (health records). Median tenure was 2.7 years. Teams were randomly assigned by the firms' HR departments to fixed office days (29 teams, 207 engineers) or flexible office days (29 teams, 205 engineers).

2.2 Measures

Output was measured as merged pull requests per engineer per week, excluding automated dependency updates. Collaboration speed was measured as the median time from a review request to the first substantive review comment. Focus time was self-reported in a fortnightly two-question survey with a response rate of 83%. Attrition counted voluntary resignations only.

2.3 Analysis

We used a difference-in-differences design with team fixed effects, comparing six months before the change with twelve months after it, and clustered standard errors at the team level. Significance was assessed at p < 0.05.

\f

3. Results

3.1 Output

Fixed-day teams merged 4.1% more pull requests per engineer per week than in their on-site baseline (95% CI: 1.2% to 7.0%). Flexible-day teams changed by 0.6%, which was not statistically significant (95% CI: -2.3% to 3.5%).

3.2 Collaboration speed

Median review turnaround fell from 11.4 hours to 9.3 hours for fixed-day teams, an 18% improvement. For flexible-day teams it rose slightly, from 11.1 to 11.8 hours. Interviews suggest that fixed days concentrated synchronous discussion, which shortened review threads.

3.3 Focus time

Self-reported uninterrupted focus time rose by 52 minutes per day on remote days in both groups. On office days it fell by 35 minutes relative to the baseline.

3.4 Attrition

Twelve-month voluntary attrition fell from 14.2% before the change to 9.6% after it, with no significant difference between the two hybrid groups. Exit interviews most often cited commute time as the reason for leaving before the change.

\f

4. Discussion

Our results suggest that hybrid work can modestly increase output when teams share fixed office days, because those days concentrate coordination. When each team picks its own days, members often miss each other, and the coordination benefit disappears. Retention gains appeared under both schedules, so firms may be able to reduce attrition without fixing office days, but they may lose the output and review-speed gains.

5. Limitations

The study covers three firms in one city and only software engineers, so the results may not generalise to other roles or regions. Focus time was self-reported. Merged pull requests measure output imperfectly, since they do not capture design work, mentoring or the size of each change. The study period overlapped with a hiring freeze at Firm B, which may have reduced attrition there for reasons unrelated to hybrid work.

6. Conclusion and Recommendations

We recommend that firms adopting hybrid work set at least two shared office days per team, schedule reviews and planning on those days, and protect remote days for focused work. Future research should test three shared days, include non-engineering roles, and measure code quality alongside volume.

Authors: Dr. Kavya Reddy (Indian Institute of Information Technology, Hyderabad) and Rohan Desai (independent researcher). Funding: none. Conflicts of interest: none declared.
