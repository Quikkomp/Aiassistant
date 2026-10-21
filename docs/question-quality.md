# New-question quality gate

`RagAgent.generate_questions` sends every newly generated set through
`question_quality.generate_reviewed_questions` before returning it to `/api/chat`.
The gate also applies when `save_to_bank` is false. Selected course materials,
topic-only generation, past-question mode and paper-style template mode all use
the same gate. No database migration or new runtime dependency is needed.

## Sequence

1. Generate a numbered, typed draft using the original requirements and source policy.
2. Check numbering, supported type labels, explicit blanks, four distinct MCQ options,
   exact duplicate questions and exposed answer/solution sections locally.
3. Send a fresh, independent review request (not the generator conversation). Include
   every question, any preface, the original instruction and the permitted factual
   context. Paper-style examples do not become factual sources.
4. Independently solve each question in the review. Require one structured verdict
   per question, actual boolean flags, recognized defect codes, reasons for rejection
   and internal reference answers/marking points for accepted questions.
5. Return only the question text if every verdict passes. Internal review answers
   and comments are not included in the response, bank, progress or student UI.
6. Regenerate the complete set on a quality/format rejection, using the original
   scope/type/count/language plus defect feedback. There are at most three drafts
   (initial + two retries). Never fall back to the last rejected draft.

The review distinguishes the requested unknown from given quantities. It rejects
"radius is 3, fill the radius" but allows "radius is 3, calculate the area" and
other legitimate repeated numbers. It does not demand one exact phrase for an
open-ended short answer; assessable marking points/equivalent wording are allowed.
Questions that depend on an absent image must not be treated as self-contained.

## Failure and budget

The model phase has a 120-second total budget and each request uses at most the
remaining time or 30 seconds. The existing OpenAI client is configured with
`max_retries=0`, so SDK retries do not multiply application retries. A valid set
normally costs one generation and one review call; at most six model calls are
made. Local format rejection can skip an unnecessary review call.

Model errors, missing/malformed/partial/truncated reviews, inconsistent verdicts
or exhaustion fail closed. `/api/chat` returns an error and releases its pending
bank reservation; an invalid set never occupies a saved bank slot. Failure text
does not echo provider exception details. The UI retains its generation indicator
until both generation and review complete and says that only approved sets save.

## Scope and limitations

This change covers new main question sets, not automatic rewriting of existing
sets, student answers, historical grades or immutable published exams. Additional
scenario/tutoring question generators are unchanged. Internal review solutions
are not a new grading-answer-key database; existing grading remains unchanged.
AI review reduces faulty questions but is not a mathematical proof or a guarantee.
Teachers must still review answers and marking criteria before publishing exams.

## Offline checks

`tests/test_question_quality.py` uses scripted model responses and temporary
SQLite databases. It covers the reported leakage example, legitimate numerical
givens, independent review payloads, all-question coverage, malformed/truncated
reviews, semantic rejection/retry limits, API failures, total-time budgets,
student-answer confidentiality and the real `/api/chat` save/failure paths.
These tests verify enforcement/control flow, not live model accuracy. No paid AI
requests, real account data, mail or production databases are used.
