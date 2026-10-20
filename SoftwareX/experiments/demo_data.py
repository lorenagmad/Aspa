# Aspa — multiple-choice exams: generate, grade and review
# Copyright (C) 2026 Lorena Gutiérrez Madroñal, Rubén Baena Pérez, José Miguel Mota Macías
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Synthetic question bank and class list used in the SoftwareX article.

All students are fictitious; identity numbers are random and do not belong to anyone.
"""
import random

from openpyxl import Workbook

# id, topic, stem, A, B, C, D, correct, group, fixed, explanation
QUESTIONS = [
    ("1", "Testing", "Which testing level verifies a single function or class in isolation?",
     "Unit testing", "System testing", "Acceptance testing", "Regression testing", "A", "T", "",
     "Unit tests exercise the smallest testable part of the program in isolation."),
    ("2", "Testing", "Which of the following are white-box techniques? (one or more answers)",
     "Statement coverage", "Branch coverage", "Equivalence partitioning", "Boundary value analysis", "AB", "T", "",
     "Coverage criteria need the code; partitioning and boundary analysis only need the specification."),
    ("3", "Testing", "Mutation testing is mainly used to...",
     "Assess the quality of a test suite", "Generate requirements", "Measure performance", "None of the above", "A", "T", "",
     "A mutant that is not killed reveals a weakness of the test suite."),
    ("4", "Testing", "A test oracle is...",
     "A mechanism that decides whether an output is correct", "A tool that generates random inputs",
     "A database of past failures", "All of the above", "A", "T", "", ""),
    ("5", "Testing", "Regression testing is performed...",
     "After every change to the code", "Only before the first release", "Only by end users", "None of the above", "A", "T", "", ""),
    ("6", "Testing", "Which statements about test-driven development are true? (one or more answers)",
     "Tests are written before the code", "It follows a red-green-refactor cycle",
     "It removes the need for integration tests", "It is only applicable to C++", "AB", "T", "",
     "TDD writes a failing test first (red), makes it pass (green) and then refactors."),
    ("7", "Testing", "Boundary value analysis for the range 1..100 would include...",
     "0, 1, 100 and 101", "Only 50", "Only negative numbers", "None of the above", "A", "T", "", ""),
    ("8", "Testing", "A flaky test is one that...",
     "Passes and fails without changes to the code", "Always fails", "Has no assertions", "Runs too fast", "A", "T", "", ""),
    ("9", "Testing", "Code coverage of 100 % guarantees that the program has no faults.",
     "True", "False", "", "", "B", "T", "",
     "Coverage shows what was executed, not whether the outputs were checked or all inputs considered."),
    ("10", "Testing", "Which levels belong to the classic V-model? (one or more answers)",
     "Unit", "Integration", "System", "All of the above", "D", "T", "", ""),
    ("11", "Requirements", "A non-functional requirement describes...",
     "A quality attribute such as performance or security", "A function the system must provide",
     "A test case", "None of the above", "A", "R", "", ""),
    ("12", "Requirements", "Which techniques are used to elicit requirements? (one or more answers)",
     "Interviews", "Workshops", "Code review", "Profiling", "AB", "R", "",
     "Interviews and workshops involve stakeholders; review and profiling work on existing code."),
    ("13", "Requirements", "A user story usually follows the template...",
     "As a <role>, I want <goal> so that <benefit>", "Given-When-Then", "IF-THEN-ELSE", "None of the above", "A", "R", "", ""),
    ("14", "Requirements", "Requirements traceability allows...",
     "Linking requirements to design, code and tests", "Compiling faster", "Removing all defects", "None of the above", "A", "R", "", ""),
    ("15", "Requirements", "Arrange from least to most formal:",
     "Natural language", "Structured natural language", "Formal specification (e.g. Z)", "None of the above", "D", "R", "ABC",
     "The order shown is from least to most formal, so no option is wrong in itself; the question asks for the arrangement."),
    ("16", "Requirements", "The MoSCoW method is used for...",
     "Prioritising requirements", "Estimating effort", "Version control", "Deployment", "A", "R", "", ""),
    ("17", "Requirements", "An acceptance criterion should be...",
     "Verifiable", "Ambiguous", "Written after release", "Optional", "A", "R", "", ""),
    ("18", "Requirements", "A use case diagram belongs to UML.",
     "True", "False", "", "", "A", "R", "", ""),
    ("19", "Requirements", "Which are characteristics of a good requirement? (one or more answers)",
     "Unambiguous", "Testable", "Implementation-specific", "Contradictory", "AB", "R", "", ""),
    ("20", "Requirements", "Scope creep refers to...",
     "Uncontrolled growth of the requirements", "A testing technique", "A design pattern", "None of the above", "A", "R", "", ""),
    ("21", "Design", "Which design pattern ensures a class has only one instance?",
     "Singleton", "Observer", "Adapter", "Decorator", "A", "", "", ""),
    ("22", "Design", "High cohesion and low coupling are desirable.",
     "True", "False", "", "", "A", "", "", ""),
    ("23", "Design", "Which of the following are SOLID principles? (one or more answers)",
     "Single responsibility", "Open/closed", "Write once, run anywhere", "Don't repeat yourself", "AB", "", "", ""),
    ("24", "Design", "The Observer pattern is a...",
     "Behavioural pattern", "Creational pattern", "Structural pattern", "None of the above", "A", "", "", ""),
    ("25", "Process", "Scrum organises the work in...",
     "Sprints", "Waterfalls", "Milestones only", "None of the above", "A", "", "", ""),
    ("26", "Process", "Continuous integration means...",
     "Merging and building changes frequently with automated tests", "Releasing once a year",
     "Writing documentation continuously", "None of the above", "A", "", "", ""),
    ("27", "Process", "Which artefacts belong to Scrum? (one or more answers)",
     "Product backlog", "Sprint backlog", "Gantt chart", "PERT network", "AB", "", "", ""),
    ("28", "Maintenance", "Refactoring changes the external behaviour of the code.",
     "True", "False", "", "", "B", "", "", ""),
    ("29", "Maintenance", "Corrective maintenance consists of...",
     "Fixing faults", "Adding features", "Porting to a new platform", "None of the above", "A", "", "", ""),
    ("30", "Maintenance", "Technical debt is...",
     "The future cost of choosing an expedient solution now", "A budget line", "A testing metric", "None of the above", "A", "", "", ""),
    ("31", "Configuration", "Which are distributed version control systems? (one or more answers)",
     "Git", "Mercurial", "Subversion", "CVS", "AB", "", "", ""),
    ("32", "Configuration", "Semantic versioning 2.0.0 increases the MAJOR number when...",
     "Incompatible API changes are made", "A bug is fixed", "Documentation changes", "None of the above", "A", "", "", ""),
    ("33", "Metrics", "Cyclomatic complexity measures...",
     "The number of independent paths through the code", "Lines of code", "Memory usage", "None of the above", "A", "", "", ""),
    ("34", "Metrics", "A high defect density always indicates poor developers.",
     "True", "False", "", "", "B", "", "", ""),
    ("35", "Quality", "ISO/IEC 25010 defines...",
     "A software product quality model", "A programming language", "A network protocol", "None of the above", "A", "", "", ""),
    ("36", "Quality", "Static analysis tools... (one or more answers)",
     "Examine the code without executing it", "Can detect potential defects", "Require a running system", "Replace testing", "AB", "", "", ""),
    ("37", "Security", "SQL injection is prevented mainly by...",
     "Parameterised queries", "Longer passwords", "Faster servers", "None of the above", "A", "", "", ""),
    ("38", "Security", "Fuzzing consists of...",
     "Feeding a program with invalid or random inputs", "Encrypting the source code", "Formal proof", "None of the above", "A", "", "", ""),
    ("39", "Usability", "Usability can be evaluated through... (one or more answers)",
     "Heuristic evaluation", "User testing", "Compilation", "Linking", "AB", "", "", ""),
    ("40", "Process", "In Kanban, a WIP limit restricts...",
     "The number of items in progress", "The number of developers", "The length of the sprint", "None of the above", "A", "", "", ""),
]

SURNAMES = ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson", "Davies", "Robinson", "Wright",
            "Thompson", "Evans", "Walker", "White", "Roberts", "Green", "Hall", "Wood", "Jackson", "Clarke",
            "García", "Fernández", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Martín", "Ruiz", "Díaz",
            "Rossi", "Müller", "Dubois", "Novak", "Silva", "Kowalski", "Jensen", "Popescu", "Horvat", "Costa"]
NAMES = ["Alex", "Sam", "Charlie", "Jamie", "Robin", "Kim", "Ariel", "Dana", "Noa", "Eli",
         "Lucía", "Hugo", "Martina", "Pablo", "Carmen", "Leo", "Inés", "Mario", "Sara", "Daniel"]


def students(n=40, seed=7):
    """Fictitious class list with DNI-, NIE- and passport-like identifiers."""
    rng = random.Random(seed)
    out = []
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    for i in range(n):
        kind = rng.random()
        if kind < 0.7:          # national ID: 8 digits + letter
            num = rng.randint(10_000_000, 99_999_999)
            doc = f"{num}{letters[num % 23]}"
        elif kind < 0.9:        # residence card: X + 7 digits + letter
            doc = f"X{rng.randint(1_000_000, 9_999_999)}{rng.choice(letters)}"
        else:                   # passport with letters
            doc = f"{rng.choice('ABCPY')}{rng.choice('ABCPY')}{rng.randint(1_000_000, 9_999_999)}"
        out.append((doc, f"{SURNAMES[i % len(SURNAMES)]}, {NAMES[(i * 7) % len(NAMES)]}"))
    return out


def write_bank(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "questions"
    ws.append(["id", "topic", "question", "A", "B", "C", "D", "correct", "group", "fixed", "explanation"])
    for q in QUESTIONS:
        ws.append(list(q))
    wb.save(path)


def write_students(path, passed=None):
    """passed: {index: 'id1, id2'} questions already passed in class (personalised exams)."""
    passed = passed or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "students"
    ws.append(["document", "name", "passed"])
    for i, (doc, name) in enumerate(students()):
        ws.append([doc, name, passed.get(i, "")])
    wb.save(path)
