# Hands-On Projects: Building AI Agents

Build these five small AI applications in order. Each project introduces a
more advanced feature while using the Groq or NVIDIA chat-completions API.
Complete the setup and API-key configuration in [README.md](./README.md) first.

## 1. Message Tone Rewriter

**Difficulty:** Beginner

Build a program that rewrites a user-provided message in a tone they choose.

**Requirements**

- Ask the user to enter a short message and choose a tone, such as friendly,
  professional, or concise.
- Send both the message and tone to either `openai/gpt-oss-120b` on Groq or
  `nvidia/nemotron-3.5-super-vl-120b-a12b` on NVIDIA.
- Ask the model to preserve the original meaning and not add new facts.
- Print the rewritten message.

**Success check:** Rewrite the same message in two different tones. Confirm
that the wording changes to match each tone while the original meaning remains
the same.

## 2. Movie Recommender

**Difficulty:** Beginner to intermediate

Build a recommender that suggests movies based on what the user wants to watch.

**Requirements**

- Ask for a genre, mood, or both.
- Recommend three movies.
- For each movie, show its title and a short reason it fits the request.
- Format the response as a numbered list.
- If the user leaves the input blank, ask them to enter a preference instead of
  sending an empty request.

**Success check:** Try different preferences, such as “funny and light” and
“science-fiction mystery.” Check that the suggestions and explanations respond
to the input.

## 3. Quiz Master

**Difficulty:** Intermediate

Build a quiz agent that asks questions about a topic chosen by the user.

**Requirements**

- Ask the user for a topic and difficulty.
- Ask one question at a time and wait for the user's answer.
- Say whether the answer is correct and briefly explain the answer.
- Keep score and show the final score after five questions.
- Do not reveal the answer before the user responds.

**Success check:** Run a quiz with correct and incorrect answers. The score
should match the answers, and the agent should wait between questions.

## 4. Multi-Turn Study Coach

**Difficulty:** Intermediate to advanced

Build a conversational coach that helps the user learn a subject over multiple
turns.

**Requirements**

- Ask which subject the user wants to study.
- Keep conversation history so follow-up questions use earlier context.
- Explain concepts in short, clear steps and ask occasional check-for-
  understanding questions.
- Provide a Rich-formatted terminal interface.
- Limit the session to 10 completed user/assistant turns and support `/exit`
  to leave early.

**Success check:** Ask a follow-up that depends on an earlier answer. Confirm
that the coach uses the conversation history, counts completed turns, and
exits when asked.

## 5. Notes-Based Question Answering Agent

**Difficulty:** Advanced

Build an agent that answers questions using notes supplied by the user, rather
than relying on general model knowledge.

**Requirements**

- Ask the user to provide or paste a set of notes.
- Accept multiple questions about those notes in the same session.
- Include the notes as context when sending each question to the model.
- Instruct the model to answer only from the provided notes. If the notes do
  not contain the answer, it should say so instead of guessing.
- Keep the note context available for follow-up questions and provide a way to
  end the session.

**Success check:** Ask one question whose answer appears in the notes and one
whose answer does not. The agent should answer the first from the notes and
clearly say the second cannot be answered from them.

**Optional extension:** For long notes, split them into paragraphs and send
only the paragraphs most relevant to each question.
