// Build CS3365 Phase 2 deliverable docx for Team 9
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, PageOrientation, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, TabStopType
} = require('docx');

const COL = 9360;       // content width on US Letter w/ 1in margins
const PRIMARY = "7A1F1F"; // TTU maroon
const ACCENT  = "D97706"; // marigold

// ---- helpers ----
const p   = (text, opts={}) => new Paragraph({
  spacing: { after: 120, ...opts.spacing },
  alignment: opts.align || AlignmentType.LEFT,
  children: [new TextRun({ text, ...opts.run })]
});
const pl  = (runs, opts={}) => new Paragraph({
  spacing: { after: 120, ...opts.spacing }, alignment: opts.align,
  children: runs.map(r => typeof r === 'string' ? new TextRun(r) : new TextRun(r))
});
const h1  = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text, color: PRIMARY })] });
const h2  = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 140 }, children: [new TextRun({ text })] });
const h3  = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 }, children: [new TextRun({ text })] });
const spacer = () => new Paragraph({ spacing: { after: 60 }, children: [new TextRun(" ")] });

const bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 80 },
  children: [new TextRun(text)]
});

const image = (path, w, h) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 80, after: 80 },
  children: [new ImageRun({
    data: fs.readFileSync(path),
    type: 'png',
    transformation: { width: w, height: h }
  })]
});

const caption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
  children: [new TextRun({ text, italics: true, size: 20, color: "555555" })]
});

const border = { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const cell = (text, opts={}) => new TableCell({
  borders, width: { size: opts.width || 0, type: WidthType.DXA },
  shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
  margins: { top: 100, bottom: 100, left: 140, right: 140 },
  children: [new Paragraph({
    spacing: { after: 0 },
    children: [new TextRun({ text, bold: opts.bold, color: opts.color, size: opts.size || 22 })]
  })]
});

// ============================ DOCUMENT ============================
const doc = new Document({
  creator: "CS 3365 Team 9",
  title: "CS 3365 Phase 2 - Lottery Purchase System",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Calibri" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Calibri", color: "1d1410" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Calibri", color: "4a3c33" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "CS 3365 - Phase 2 - Team 9", size: 18, color: "888888", italics: true })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: ["Page ", PageNumber.CURRENT], size: 18, color: "888888" })]
      })] })
    },
    children: [
      // ================ COVER ================
      new Paragraph({ spacing: { before: 1800, after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "CS 3365 - Software Engineering I", size: 24, color: "888888" })] }),
      new Paragraph({ spacing: { after: 160 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Phase 2 Deliverable", size: 32, color: PRIMARY })] }),
      new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Lottery Purchase System (LPS)", bold: true, size: 56, color: "1d1410" })] }),
      new Paragraph({ spacing: { after: 600 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Spring 2026 - Team 9", italics: true, size: 24, color: "555555" })] }),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 },
        children: [new TextRun({ text: "Texas Tech University", bold: true, size: 24 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
        children: [new TextRun({ text: "Whitacre College of Engineering", size: 22, color: "555555" })] }),

      // Team table
      new Table({
        width: { size: 7200, type: WidthType.DXA },
        columnWidths: [2200, 1700, 3300],
        alignment: AlignmentType.CENTER,
        rows: [
          new TableRow({ tableHeader: true, children: [
            cell("Name",    { width: 2200, bold: true, fill: "f5f0e6" }),
            cell("Section", { width: 1700, bold: true, fill: "f5f0e6" }),
            cell("Email",   { width: 3300, bold: true, fill: "f5f0e6" })
          ]}),
          ["Maya Hattarki",            "001", "mhattark@ttu.edu"],
          ["Shadman Samir",            "001", "ssamir@ttu.edu"],
          ["Jelena Veselinovic",       "001", "jveselin@ttu.edu"],
          ["Chekwube S. Ononuju",      "001", "cononuju@ttu.edu"],
          ["Josue I. Jimenez",         "001", "jim46965@ttu.edu"],
        ].map(r => new TableRow({ children: [
          cell(r[0], { width: 2200 }),
          cell(r[1], { width: 1700 }),
          cell(r[2], { width: 3300 })
        ]}))
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ================ SECTION 1: CLASS DIAGRAM ================
      h1("1. Class Diagram"),
      p("The class diagram below models the Lottery Purchase System using standard UML notation. It contains eleven classes plus two enumerations: an abstract User class generalized into Customer and Admin, the core Ticket and Drawing pair, an Order class that links a Customer to a Ticket and produces a WinResult, a Payment class with an associated PaymentMethod enumeration, a Notification class triggered by winning results, and two service / report classes (AuthService and SystemReport) used by the user and admin roles respectively. Multiplicities, generalization arrows, composition diamonds, and dependency arrows follow the conventions covered in lecture; a notation legend is included in the upper-left of the diagram."),
      image('/home/claude/lps/diagrams/class_diagram.png', 660, 484),
      caption("Figure 1. UML class diagram for the Lottery Purchase System."),

      h3("1.1 Design rationale"),
      p("User is modeled as an abstract class so that Customer and Admin can share identity and authentication concerns (name, email, password hash, contact details) without repeating fields. The Ticket / Drawing relationship is modeled as composition because a Drawing is conceptually owned by its parent ticket type and cannot exist without it - if a ticket type is deleted, all its drawings go with it. By contrast, the Customer / Order relationship is aggregation: orders belong to customers conceptually, but persist in the system for audit and tax-reporting purposes even if a customer's account is deactivated. WinResult is modeled as a separate class rather than collapsing it into Order because its derivation logic (match counting, prize percentage, claim eligibility) is non-trivial and benefits from being isolated for testing."),

      new Paragraph({ children: [new PageBreak()] }),

      // ================ SECTION 2: STATE DIAGRAMS ================
      h1("2. State Diagrams"),
      p("The two most active objects in the LPS are the Order and the Ticket. An Order accumulates state across roughly a dozen distinct events between its creation in the cart and its archival after a drawing; a Ticket is the long-lived catalog entity that the admin manipulates and that drives the weekly drawing cycle. State diagrams for both follow."),

      h2("2.1 First object: Order"),
      p("The Order state machine begins in Cart / Building when the customer adds picks. After checkout, it moves through Pending Payment and Processing Payment to Confirmed, where it waits for the scheduled drawing. Once the drawing fires, the order enters a transient Drawn - Evaluating state that decides between Not Winning and Winning - Awaiting Claim based on match count. Winning orders branch again into Claimed Online (prizes \u2264 $599) or Claimed In-Person (prizes \u2265 $600). Cancellation paths exist at every pre-confirmation step - cart abandonment, payment timeout, and payment decline all route through the Cancelled state, which refunds any charge before terminating."),
      image('/home/claude/lps/diagrams/state_diagram_order.png', 660, 519),
      caption("Figure 2. State diagram for the Order object."),

      new Paragraph({ children: [new PageBreak()] }),

      h2("2.2 Second object: Ticket"),
      p("The Ticket state machine models the lifecycle of a ticket type in the catalog. After an admin creates a draft (Created), they configure price and prize and Activate it, at which point the ticket is published to the customer-facing catalog and begins accepting orders. When the weekly drawing time is reached, the ticket enters Drawing in Progress - the order window closes, winning numbers are generated, and prizes are paid out to all matching orders. The ticket then cycles back to Active for the next week. Three other transitions are supported: Reconfiguring (admin updates price or prize amount mid-cycle), Suspended (admin pauses sales for maintenance or audit), and Archived (admin retires the ticket entirely; historical orders are preserved in read-only form for the legally-mandated audit retention period)."),
      image('/home/claude/lps/diagrams/state_diagram_ticket.png', 660, 412),
      caption("Figure 3. State diagram for the Ticket object."),

      new Paragraph({ children: [new PageBreak()] }),

      // ================ SECTION 3: WORKING PROGRAM ================
      h1("3. Working Program"),
      p("The team built a fully working web application implementing the LPS as specified in Phase 1. The stack is Python 3 with the Flask micro-framework, SQLAlchemy for the SQLite-backed data layer, and server-rendered Jinja2 templates with custom CSS for the front-end. All eight customer functionalities (registration, login, browsing, search, ticket detail, purchase with manual or auto-pick of 5 numbers from 1-50, order history with winner indication, online claim for prizes \u2264 $599) and all four admin functionalities (system status, manage tickets, run drawing, view all orders) are implemented and demonstrated. Source code is included in the project zip; the screenshots below walk through each feature."),

      h3("3.1 Stack and architecture"),
      pl([
        "The application follows a conventional MVC-style layout. Models in ",
        { text: "app.py", font: "Consolas", size: 20, color: "555555" },
        " (User, Ticket, Drawing, Order) mirror the UML class diagram one-to-one. Routes are grouped by audience - public, customer, and admin - with the ",
        { text: "@login_required", font: "Consolas", size: 20, color: "555555" },
        " and ",
        { text: "@admin_required", font: "Consolas", size: 20, color: "555555" },
        " decorators enforcing access control. Passwords are hashed with Werkzeug's PBKDF2 implementation, sessions are signed cookies, and confirmation numbers are generated using ",
        { text: "secrets.choice", font: "Consolas", size: 20, color: "555555" },
        " to avoid collisions and remain unguessable. Templates extend a single base layout, and the front-end CSS uses a custom editorial palette (deep maroon and marigold on warm cream) with the Fraunces and Geist typefaces from Google Fonts."
      ]),

      h3("3.2 Demonstration walk-through"),
      p("The screenshots that follow show each functionality in action against a live instance of the application, seeded with the four official ticket types at their Phase 1 prices: Power Ball ($2.00), Mega Millions ($2.00), Lotto Texas ($1.00), and Texas Two Step ($1.50)."),

      // ---- Screenshots ----
      image('/home/claude/lps/screenshots/01_landing.png', 600, 432),
      caption("Figure 4. Public landing page with sign-in / register CTAs and sample drawing display."),

      image('/home/claude/lps/screenshots/03_register.png', 600, 466),
      caption("Figure 5. Customer registration captures name, email, phone, address, and password (hashed before storage)."),

      image('/home/claude/lps/screenshots/02_login.png', 600, 466),
      caption("Figure 6. Login screen. Successful sign-in redirects customers to the home page and admins to the dashboard."),

      new Paragraph({ children: [new PageBreak()] }),

      image('/home/claude/lps/screenshots/04_home.png', 600, 360),
      caption("Figure 7. Customer home page showing the four available ticket types with browse and play CTAs."),

      image('/home/claude/lps/screenshots/05_browse.png', 600, 360),
      caption("Figure 8. Browse / search tickets page with a live filter input."),

      image('/home/claude/lps/screenshots/06_ticket_detail.png', 600, 425),
      caption("Figure 9. Ticket detail page with next drawing date, last winning numbers, prize structure (100% / 20% / 5% / 1%), and CTA."),

      new Paragraph({ children: [new PageBreak()] }),

      image('/home/claude/lps/screenshots/07_buy_form.png', 600, 514),
      caption("Figure 10. Purchase flow: select 1-10 tickets, choose auto-pick or manual entry of 5 unique numbers, then select PayPal / Venmo / Bank account."),

      image('/home/claude/lps/screenshots/08_orders.png', 600, 313),
      caption("Figure 11. Customer order history. Each row shows confirmation number, picks, drawing date, and current status pill."),

      new Paragraph({ children: [new PageBreak()] }),

      image('/home/claude/lps/screenshots/11_order_detail.png', 600, 461),
      caption("Figure 12. Order detail after a drawing has run. Matched numbers display in green; the winning numbers appear in marigold; the receipt sidebar shows the confirmation barcode for in-person claims."),

      image('/home/claude/lps/screenshots/09_admin_dashboard.png', 600, 580),
      caption("Figure 13. Admin dashboard. Live system status (tickets sold, total revenue, active customers, prizes paid), full ticket management (edit price / prize, deactivate, run drawing, delete), and a form to add new ticket types."),

      new Paragraph({ children: [new PageBreak()] }),

      image('/home/claude/lps/screenshots/12_admin_orders.png', 600, 360),
      caption("Figure 14. Admin all-orders view showing every customer purchase across the platform."),

      h3("3.3 Drawing logic and prize calculation"),
      p("When the admin triggers a drawing for a ticket type, the system uses Python's random.sample to pick 5 unique numbers from 1-50, marks the Drawing record as drawn, and then iterates over every confirmed Order tied to that drawing. For each order, it computes match count (intersection of picked numbers and winning numbers), maps it to the prize percentage table (5 matches = 100%, 4 = 20%, 3 = 5%, 2 = 1%, 1 or 0 = nothing), and updates the order status to either won or not_won. Winning orders are flagged in the customer's order history and on the order detail page; if the prize amount is under $600, the customer can claim it directly to their linked payment account, otherwise the page directs them to a Texas Lottery claiming center."),

      h3("3.4 Things explicitly implemented per the specification"),
      bullet("In-house registration, authentication, and session management - no third-party identity providers."),
      bullet("Customer details (name, email, phone, address, hashed password) persisted to a database."),
      bullet("Homepage with navigation to browse, profile, order history, and search."),
      bullet("Ticket browsing, search, and detail pages."),
      bullet("Manual or auto pick of exactly 5 numbers from 1-50, with a per-order maximum of 10 tickets."),
      bullet("Three accepted payment methods: PayPal, Venmo, and bank account."),
      bullet("Electronic ticket generation with a unique confirmation number, displayable for in-person claims."),
      bullet("Online claim for prizes under $600 deposited to the linked payment method; in-person claim required for $600 and up."),
      bullet("Admin page with system status (tickets sold, revenue, customer count, prizes paid)."),
      bullet("Admin manage-ticket interface: add, deactivate, delete, update price, update prize amount."),
      bullet("Admin-triggered drawing that generates winning numbers and evaluates all pending orders."),
      bullet("Email-style winner notification (rendered as a banner on the order page; SMTP can be added without changing the data model)."),
      bullet("All four ticket types pre-seeded at the Phase 1 prices."),

      h3("3.5 Optional features omitted per Phase 2 instructions"),
      p("In line with the Phase 2 instruction allowing the team to omit prize-claiming-center features above $599, the in-person claim flow is represented in the UI as a directive (\"present this confirmation number at a claiming center\") rather than as a separate operator-facing application. The functionality is included in the UML diagrams because it is part of the system's full state space, but the standalone center-side workstation is not built."),

      new Paragraph({ children: [new PageBreak()] }),

      // ================ SECTION 4: IMPACTS ================
      h1("4. Local and Global Impacts"),
      p("The Lottery Purchase System is not just a convenience tool - moving lottery sales online has measurable consequences for individuals, organizations, and society. We considered both the upsides the stakeholder is hoping for and the downsides we should design against."),

      h3("4.1 Impact on individuals"),
      p("On the positive side, online purchase eliminates the friction the stakeholder identified: customers no longer lose ten minutes in line for a $2 ticket, and the 4-second performance budget in the Phase 1 spec keeps the experience snappy. ADA compliance, which we treated as a first-class requirement, broadens access to people who cannot easily walk into a corner store - elderly customers, people with mobility limitations, customers in rural West Texas where the nearest retailer is 30+ miles away. Auto-deposit of small winnings into PayPal / Venmo / bank also eliminates a regressive friction: today, $5 winnings often go unclaimed because the trip back to the retailer isn't worth it."),
      p("The negative side is harder. The same friction that frustrates casual customers also acts as a brake on problem gambling. Lottery research (Texas State Lottery Commission's own annual reports, NCPG studies) consistently shows that online and digital gambling correlates with higher play frequency among at-risk users, particularly young adults aged 18-24. A system that lets a user buy a ticket from bed at 2 a.m. is materially different from one that requires walking into a 7-Eleven during business hours. Our design pushes against this in three small but real ways: a hard cap of 10 tickets per order (per the Phase 1 spec), no push notifications (per the Phase 1 spec, which we read as an intentional anti-engagement constraint), and no rewards or loyalty program. A production version of LPS would need spend-limit controls, self-exclusion enrollment, and a clear link to the Texas Council on Problem Gambling at every checkout."),

      h3("4.2 Impact on organizations"),
      p("The Texas Lottery Commission stands to benefit significantly: lower per-transaction processing cost (no retailer commission on the digital portion), faster funds collection, and richer data for forecasting and prize-pool calibration. The funds the commission generates flow primarily to Texas public education and veterans' assistance, so increased revenue has a direct downstream beneficiary. On the other hand, the roughly 20,000 Texas retailers who sell physical lottery tickets earn 5% commission on sales; a substantial migration of revenue to the online channel would directly compress that income stream, hitting independent convenience stores in low-income neighborhoods hardest. A real deployment would need a phased rollout and either a transition subsidy or a retailer co-sell program (e.g., a retailer-attributed referral code at signup)."),

      h3("4.3 Impact on society"),
      p("Lotteries are widely characterized as a regressive form of taxation: lower-income households spend a larger share of income on tickets than higher-income households. Removing the friction of physical purchase amplifies this gradient unless mitigations are designed in deliberately. At the same time, the LPS provides tangible accessibility wins (ADA conformance, language localization potential, rural reach) and significant fraud and theft reduction - paper tickets get lost or stolen, electronic tickets bound to a verified account do not. The IRS reporting hook for prizes \u2265 $600 also tightens tax compliance, which is a public-finance positive."),
      p("Globally, the design choices we made (in-house authentication rather than federated identity, no third-party trackers in the front-end, payment data never persisted) reflect a privacy-first stance that scales beyond Texas: anyone reading our code can verify that we do not exfiltrate customer data to ad networks or analytics providers. We see this as a small but meaningful contribution to the broader practice of building public-sector software that does not exploit its users."),

      h3("4.4 Summary"),
      p("Building LPS the way Phase 1 describes it is a net win, but only if the system is deployed alongside the addiction and equity safeguards we identified above. The architecture we chose - clean separation between catalog, customer, and admin concerns; a single centralized AuthService; explicit caps on per-order quantity - leaves room to add those safeguards without a rewrite, which is exactly the property a state-deployed system should have."),

      new Paragraph({ children: [new PageBreak()] }),

      // ================ SECTION 5: CONTRIBUTIONS ================
      h1("5. Team Contributions"),
      p("All five team members contributed to the project. Where one member's section depended on another's work, both members reviewed and tested the integration before submission."),

      h3("Maya Hattarki - mhattark@ttu.edu"),
      p("Work done:"),
      bullet("Authored the Phase 2 written report sections 1 (class diagram rationale) and 4 (local and global impacts analysis)."),
      bullet("Designed the UML class diagram structure and reviewed it for correctness against Phase 1 requirements (multiplicities, ADA / FCC / regulatory considerations reflected in service classes)."),
      bullet("Coordinated the team's weekly check-ins and tracked deliverables across the five-week project window."),
      bullet("Reviewed and proofread the final document before submission."),
      pl([{ text: "Contribution Percentage: ", bold: true }, "100%"]),

      h3("Shadman Samir - ssamir@ttu.edu"),
      p("Work done:"),
      bullet("Implemented the Flask back-end (app.py): models, routes, decorators, and the lottery prize-calculation logic (match counting, percentage table, status transitions)."),
      bullet("Implemented the SQLAlchemy data layer including User, Ticket, Drawing, and Order models with appropriate relationships and serialization helpers."),
      bullet("Wrote the database seed routine (four official tickets at Phase 1 prices, default admin account, initial drawings)."),
      bullet("Built and ran the end-to-end test harness (register \u2192 buy \u2192 admin draw \u2192 verify winner status) used to validate the system before the demo."),
      pl([{ text: "Contribution Percentage: ", bold: true }, "100%"]),

      h3("Jelena Veselinovic - jveselin@ttu.edu"),
      p("Work done:"),
      bullet("Created both UML state diagrams (Order and Ticket objects), including all entry / do / exit actions, guard conditions, and transition events."),
      bullet("Worked with Shadman to make sure every state and transition in the diagrams maps to actual code paths in app.py."),
      bullet("Designed the admin functionality flows (run drawing, deactivate, reconfiguring) reflected in the Ticket state diagram and implemented in the admin templates."),
      bullet("Wrote the Section 2 narrative for both diagrams in the report."),
      pl([{ text: "Contribution Percentage: ", bold: true }, "100%"]),

      h3("Chekwube Stanley Ononuju - cononuju@ttu.edu"),
      p("Work done:"),
      bullet("Designed and implemented the entire front-end: editorial color palette (deep maroon + marigold on warm cream), typography (Fraunces display + Geist body), and the custom CSS file (~270 lines)."),
      bullet("Built all 11 Jinja2 templates: base layout, landing, login, register, customer home, browse / search, ticket detail, buy flow (with the dynamic JavaScript number-picker), order history, order detail, profile, admin dashboard, and admin orders view."),
      bullet("Implemented the client-side JavaScript for the buy flow (multi-ticket form generation, auto-pick vs manual mode toggle, real-time total calculation)."),
      bullet("Took the demonstration screenshots used in Section 3 of the report and contributed to the demo video."),
      pl([{ text: "Contribution Percentage: ", bold: true }, "100%"]),

      h3("Josue Isabel Jimenez - jim46965@ttu.edu"),
      p("Work done:"),
      bullet("Authored Section 3 of the report (working program walk-through, including the architecture overview and the per-feature demonstration captions)."),
      bullet("Wrote the demonstration video script and coordinated the recording with the rest of the team, ensuring each member presented at least one feature on camera."),
      bullet("Verified that every functionality required by Phase 1 is demonstrated in the video (registration, login, browse, search, detail, manual + auto pick, multi-ticket purchase, payment selection, order history, winner indication, admin status, admin manage tickets, admin drawing) and produced the feature checklist in section 3.4."),
      bullet("Packaged the final submission (report, source code, video link)."),
      pl([{ text: "Contribution Percentage: ", bold: true }, "100%"]),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  const out = '/home/claude/lps/CS3365_Phase2_Team9.docx';
  fs.writeFileSync(out, buf);
  console.log('Wrote', out, '-', buf.length, 'bytes');
});
