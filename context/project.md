PROJECT PROPOSAL
BankSense
Intelligent NLP-Based Banking Complaint Analysis & Triage
Natural Language Processing • Machine Learning • FinTech
EXECUTIVE SUMMARY — READ THIS FIRST
BankSense is a two-person, two-day MVP that analyses banking-related customer messages. It predicts complaint intent, suggests priority using transparent rules, retrieves semantically similar past cases, creates a short summary and displays complaint patterns on a dashboard. The goal is to reduce the manual effort involved in the initial sorting and understanding of support queries.
AT A GLANCE	DETAIL
Problem	Large volumes of unstructured banking queries must be understood, categorised and routed.
Users	Bank support teams, complaint-resolution teams, operations teams and customer-service managers.
Core NLP	TF-IDF, Logistic Regression, Sentence-BERT embeddings and cosine similarity.
Product	React interface + Flask API + SQLite + trained NLP models.
Dataset	BANKING77: 13,083 labelled banking queries across 77 intent classes.
Duration	Two days for a functional prototype; scope is limited to an MVP.
Deliverable	A working complaint-analysis application plus a measured comparison of two classification approaches.

1. Project Overview
BankSense is an NLP-powered banking complaint intelligence platform designed to automate the initial analysis, classification and prioritisation of customer messages. It converts unstructured text into structured information that can help support teams review and organise incoming cases. The system is a decision-support prototype, not an autonomous complaint-resolution or banking transaction system.
2. Problem Statement
Banks and financial service providers receive customer messages about failed transfers, duplicate charges, cash withdrawals, card payments, refunds and account access. Manually reviewing and sorting these messages takes time; similar cases may be investigated separately; and recurring problems can be difficult to identify. BankSense explores how NLP can understand banking-related text, predict intent, retrieve related cases and provide a concise operational view.
3. Proposed Solution and Core Features
3.1 Intent classification
Predict the intent of a submitted query, such as failed transfer, duplicate charge, cash withdrawal issue or refund request. Return the predicted label and model confidence.
3.2 Priority suggestion
Combine predicted intent with predefined business rules to suggest priority. For example, a report of an unauthorised card transaction may trigger critical priority. This is rule-assisted triage, not a trained fraud detector.
3.3 Semantic similarity
Use Sentence-BERT embeddings and cosine similarity to retrieve stored complaints with similar meaning, rather than relying only on exact keyword matches.
3.4 Complaint summarisation
Generate a concise summary of a longer complaint using a pretrained summarisation model or an available language-model API.
3.5 Analytics dashboard
Show complaint counts, intent distribution, priority breakdown and frequently occurring issues based on records processed by the prototype.
4. Target Users and Expected Value
Target user	Potential value
Bank customer-support teams	Faster first-pass understanding and categorisation of messages.
Complaint-resolution teams	Find related historical examples for reference.
Banking operations teams	View complaint categories and recurring operational issues.
Customer-service managers	Monitor complaint patterns and priority distribution.
FinTech support teams	Explore an automated workflow for organising customer queries.

5. Dataset
The project will use BANKING77, a publicly available banking intent-classification dataset. It contains 13,083 customer-service queries across 77 intent categories: 10,003 training examples and 3,080 test examples.
Dataset source: PolyAI BANKING77 — https://huggingface.co/datasets/PolyAI/banking77
Limitation: BANKING77 is a labelled benchmark of banking-related queries, not verified internal complaint records from a bank. Additional sample records may be created to demonstrate storage, similarity retrieval and dashboard workflows; demo data must be labelled as such.
6. Technology Stack
Layer	Technology / method	Purpose
Language	Python	Core ML/NLP implementation.
Data handling	Pandas, NumPy	Dataset exploration and preparation.
Text processing	NLTK / basic preprocessing	Prepare text for modelling.
Baseline classifier	TF-IDF + Logistic Regression	Traditional ML text classification.
Embedding classifier	Sentence-BERT + Logistic Regression	Classification using sentence representations.
Similarity retrieval	Sentence-BERT + cosine similarity	Find semantically related complaints.
Summarisation	Pretrained model or API	Create concise complaint summaries.
Backend	Flask REST API	Expose model and application functions.
Frontend	React.js	Complaint submission and dashboard.
Database	SQLite	Store complaints and prediction outputs.
Visualisation / evaluation	Plotly / Scikit-learn	Dashboard charts and model metrics.

7. Methodology and Model Evaluation
Two classification pipelines will be implemented and compared using the same training/test split:
    1. Baseline: TF-IDF vectorisation followed by Logistic Regression.
    2. Embedding-based: Sentence-BERT sentence embeddings followed by Logistic Regression.
Evaluation will report accuracy, precision, recall, F1-score and a confusion matrix. Macro-F1 is particularly useful across 77 classes because it gives each class more balanced importance. Keep the test set separate from training and model selection. Report measured results only; do not invent or promise a target accuracy.
8. System Workflow
    3. Customer enters a banking-related query in the React interface.
    4. React sends the text to the Flask API.
    5. The backend preprocesses the text and runs the intent classifier.
    6. The system returns the predicted intent and confidence.
    7. Predefined rules suggest a priority based on the intent and relevant text conditions.
    8. Sentence embeddings retrieve similar stored complaints.
    9. A summarisation component generates a concise description when requested.
    10. The complaint and its outputs are stored in SQLite and reflected in dashboard analytics.
9. Two-Day Implementation Plan
Timeline	Member 1 — NLP / ML	Member 2 — Backend / UI
Day 1	Explore BANKING77; preprocess data; train TF-IDF + Logistic Regression; generate Sentence-BERT embeddings; evaluate models.	Set up Flask; create API structure; design SQLite schema; implement complaint storage and similarity endpoint.
Day 2	Integrate classifier; implement priority rules; add summarisation; validate outputs and evaluation.	Build React complaint form, results view and dashboard; connect APIs; support integration and testing.

Both members jointly handle integration, end-to-end testing, bug fixing and the final demonstration. If time becomes tight, prioritise classification, similarity retrieval, complaint submission and results display. Summarisation and advanced dashboard polish are secondary.
10. Expected Deliverables
    • A prepared BANKING77 data pipeline.
    • Two trained intent-classification approaches and a reproducible comparison.
    • A working complaint-intent prediction API.
    • Rule-assisted priority suggestions.
    • Semantic retrieval of similar complaints.
    • A basic complaint summary feature, subject to model/API availability.
    • A React interface with complaint submission and results.
    • A basic SQLite-backed analytics dashboard.
    • A README documenting setup, architecture, dataset, evaluation and limitations.
11. Scope and Limitations
    • The MVP focuses on English-language banking queries represented by BANKING77.
    • The prototype supports initial triage and decision support; a human reviews and acts on complaints.
    • Priority is suggested using explicit rules and predicted intent; it is not a validated risk or fraud score.
    • The dataset does not establish real bank complaint volumes, service-level agreements or operational outcomes.
    • No live banking APIs, payment systems, customer identity records or confidential bank data will be connected.
    • A two-day build can produce a demonstrable MVP, not a production-ready enterprise system.
12. Future Enhancements
    • Evaluate on authorised, anonymised complaint data from a real support environment.
    • Add multilingual query support.
    • Add human feedback and correction workflows to improve predictions.
    • Integrate with ticketing or CRM platforms through secure APIs.
    • Improve explainability by showing evidence behind predictions.
    • Monitor model drift and performance over time.
13. Resume and Learning Outcomes
The project demonstrates applied NLP, supervised classification, transformer-based text representations, semantic retrieval, model evaluation and full-stack integration. It is relevant to AI/ML, NLP, software engineering and fintech engineering internship discussions.
Suggested resume description (use after implementation):
Built BankSense, an NLP-based banking complaint triage prototype using TF-IDF, Logistic Regression and Sentence-BERT; compared intent-classification approaches, implemented semantic retrieval and rule-assisted priority suggestions, and integrated the models into a Flask and React application.
14. Conclusion
BankSense applies NLP and machine learning to a defined financial-services workflow: understanding and organising incoming banking queries. By combining a measurable classification experiment with semantic retrieval and a usable application interface, the project aims to deliver a technically meaningful prototype within a constrained two-day development window.