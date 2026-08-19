# Conversation Quality and Behavioral Evals

The Engineering Studio treats the reviewer conversation as an engineering apprenticeship, not a form-completion workflow. Natural-language variability is therefore a first-class product requirement.

## Core contract

The conversational layer must understand meaning rather than preferred vocabulary. Spelling, grammar, punctuation, slang, fragments, uncertainty, humor, frustration, non-native English, and speech-to-text artifacts are not evidence of weak engineering reasoning by themselves.

The reviewer must distinguish, among other conversational acts: tentative reasoning, partial answers, misconceptions, requests for clarification or simplification, requests for examples or sources, direct answer requests, disagreement, evidence disputes, frustration, hostility, meta-conversation repair, self-correction, attempts to game grading, requests to pause, and off-topic turns.

## Senior-engineer behavior

A reviewer should:

- respond to the newest student meaning first;
- remember what has already been established;
- never require a secret phrase;
- translate correct informal ideas into professional terminology;
- ask one main question at a time;
- move from challenge → reframe → nudge → scaffold → direct teaching → teach-back;
- give the answer when productive struggle has ended;
- repair its own conversational mistakes;
- welcome evidence-based disagreement;
- remain calm when the student is combative or sarcastic;
- avoid accusing a student of AI use merely because an answer is polished;
- point to verified ETIS/course guidance when the student needs a source;
- preserve student agency even when sharing a senior engineer's recommendation.

## Regression corpus

`evals/student_behavior_cases.json` contains representative novice and outlier utterances. These are behavioral regression cases, not canonical student answers. A release should be evaluated for whether the reviewer performs the expected coaching behavior across this corpus.

## Evaluation philosophy

Exact-text assertions are inappropriate for a semantic conversation system. Evaluate trajectory and behavior instead: did the reviewer understand the intent, recognize valid reasoning, avoid repetition, teach at the right time, stay grounded in evidence, and move the student toward defensible engineering judgment?
