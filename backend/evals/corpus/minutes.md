# Product Steering Committee — Minutes, 14 August 2026

SYNTHETIC DOCUMENT written for evaluating Margin. The company, people and decisions are fictional.

Company: Tidewater Health (patient-scheduling software). Meeting held by video call, 10:00 to 11:30 IST.

Attendees: Sana Qureshi (VP Product, chair), Daniel Thomas (Head of Engineering), Priyanka Bose (Design Lead), Farhan Ali (Customer Success), Lin Wei (Finance). Apologies: Neha Kulkarni (Sales).

1. Q3 Roadmap Status

Daniel reported that the online check-in feature shipped on 2 August, eleven days later than planned, because the insurance-verification partner changed its API. Adoption reached 31% of clinics in the first ten days. The SMS reminder redesign is on track for 30 September. The analytics dashboard has slipped to Q4 because two engineers moved to the check-in incident response.

\f

2. Customer Feedback

Farhan presented the July support data: 1,240 tickets, down 9% from June. The top complaint was double-booking when two receptionists edit the same calendar slot at once; it caused 212 tickets. Three enterprise clinics said they would not renew in January unless double-booking is fixed. Priyanka shared usability test results from 8 receptionists: 6 of 8 could not find the waitlist feature without help.

3. Decisions

The committee decided to make the double-booking fix the top engineering priority for September, ahead of the analytics dashboard. The committee approved moving the waitlist into the main calendar view instead of the settings menu. The committee rejected the proposal to raise the base subscription price in October; it will be reconsidered after the January renewals. Budget of INR 18 lakh was approved for a second insurance-verification partner, to reduce dependence on a single vendor.

\f

4. Risks

Lin flagged that if the three enterprise clinics churn, annual recurring revenue would fall by about INR 1.1 crore. Daniel flagged that the double-booking fix needs a database migration that will require a 30-minute maintenance window. Priyanka noted the design team has no researcher until the new hire starts in October.

5. Action Items

Daniel Thomas to deliver a technical plan for the double-booking fix, including the migration and rollback approach, by 21 August. Priyanka Bose to share the waitlist redesign prototype by 28 August. Farhan Ali to schedule calls with the three at-risk enterprise clinics before 31 August and share their requirements. Lin Wei to model the revenue impact of a delayed price change by 4 September. Sana Qureshi to send the updated Q3 roadmap to the leadership team by 18 August.

6. Next Meeting

The next steering committee meeting is on 11 September 2026 at 10:00 IST. The double-booking technical plan and the waitlist prototype will be the main agenda items.
