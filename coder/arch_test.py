#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Reasoning Lab Test
Category: Data structures + Logical chains + Error handling (architecture review)
Topic: Android Compose streaming chat screen (state isolation, side-effects, multi-conversation)
Python: 3.9+ (stdlib only)
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TestCase:
    test_id: str
    title: str
    difficulty: str
    prompt: str
    buggy_code: str
    expected_reasoning_steps: List[str]
    pass_score: int = 80


class ComposeArchitectureTest:
    """
    Complex architectural test: identify non-obvious critical bug + propose refactor + code fix.
    Evaluation is text-based (LLM answer), scoring via heuristics.
    """

    def __init__(self) -> None:
        self.case = TestCase(
            test_id="ARCH_COMPOSE_CHAT_003",
            title="Compose Chat: Multi-Conversation Streaming + Smart Auto-scroll",
            difficulty="Expert",
            prompt=self._prompt(),
            buggy_code=self._buggy_code(),
            expected_reasoning_steps=[
                "Detect that streaming buffer is global and not scoped/cleared per conversationId; propose scoping or filtering.",
                "Isolate high-frequency updates: do not rebuild whole uiState on each token; separate messages flow or use distinctUntilChanged/derived state.",
                "Fix auto-scroll: avoid triggering side-effects on each token/content mutation; react to message count or explicit events.",
                "Use stable keys in LazyColumn; avoid positional identity leaks.",
                "Ensure cancellation & race handling when conversationId changes (flatMapLatest + cleanup).",
            ],
            pass_score=80,
        )

    # ---------- Public API ----------
    def get_input(self) -> str:
        return self.case.prompt + "\n\n=== BUGGY CODE (KOTLIN) ===\n" + self.case.buggy_code

    def get_expected_output_description(self) -> str:
        return (
            "LLM must: (1) name root causes tied to symptoms, (2) propose refactor plan, "
            "(3) provide corrected code for ChatViewModel + ChatContent under constraints."
        )

    def evaluate(self, llm_answer: str) -> Dict[str, object]:
        score = 0
        feedback: List[str] = []

        # --- A) Critical hidden bug: streaming buffer cross-conversation leakage ---
        # Expect mention: scope buffer by conversationId, clear buffer on switch,
        # or store buffer as Map<conversationId, Map<messageId, chunk>>.
        cross_conv_patterns = [
            r"buffer.*conversation",
            r"streaming.*buffer.*(scoped|scope|per)\s+conversation",
            r"clear.*buffer.*(on|when).*conversation",
            r"flatMapLatest.*conversation",
            r"key.*(conversationId).*buffer",
            r"leak.*(conversation|chat)",
        ]
        if self._any(cross_conv_patterns, llm_answer):
            score += 35
            feedback.append("SUCCESS: Identified cross-conversation streaming buffer leak / scoping issue.")
        else:
            feedback.append("FAIL: Missed critical bug: streaming buffer not scoped to conversationId (ghost tokens in other chats).")

        # --- B) High-frequency update isolation ---
        # Expect: split uiState, messages as separate flow, avoid combine of everything on each token,
        # apply distinctUntilChanged, stateIn/shareIn appropriately.
        perf_patterns = [
            r"distinctUntilChanged",
            r"separate.*(flow|state).*messages",
            r"split.*uiState",
            r"avoid.*rebuild.*uiState",
            r"shareIn|stateIn",
            r"only.*update.*last\s+message",
        ]
        if self._any(perf_patterns, llm_answer):
            score += 25
            feedback.append("SUCCESS: Proposed isolating high-frequency streaming updates (reduce recomposition pressure).")
        else:
            feedback.append("FAIL: Did not propose isolating high-frequency updates; likely keeps full-screen recompositions.")

        # --- C) Scroll jitter / side-effects correctness ---
        # Expect: avoid LaunchedEffect(messages) on streaming, use size/events, snapshotFlow, collectLatest, debounce, etc.
        scroll_patterns = [
            r"snapshotFlow",
            r"LaunchedEffect\s*\(\s*messages\s*\)",
            r"LaunchedEffect\s*\(\s*messages\.size\s*\)",
            r"collectLatest",
            r"debounce|throttle",
            r"scrollToItem|animateScrollToItem",
            r"isScrollInProgress",
        ]
        # If they still explicitly recommend LaunchedEffect(messages) without caveats, penalize.
        if re.search(r"LaunchedEffect\s*\(\s*messages\s*\)", llm_answer, re.IGNORECASE):
            score -= 10
            feedback.append("WARNING: Mentions LaunchedEffect(messages) which is risky under streaming; needs strong justification.")
        if self._any(scroll_patterns, llm_answer):
            score += 20
            feedback.append("SUCCESS: Addresses scroll side-effects under streaming (jitter/race/cancellation).")
        else:
            feedback.append("FAIL: No solid plan for auto-scroll stability during streaming.")

        # --- D) Stable keys & list identity ---
        key_patterns = [
            r"key\s*=\s*\{\s*it\.id\s*\}",
            r"stable\s+key",
            r"LazyColumn.*key",
            r"positional\s+key|index\s+as\s+key",
        ]
        if self._any(key_patterns, llm_answer):
            score += 10
            feedback.append("SUCCESS: Mentions stable LazyColumn keys / identity.")
        else:
            feedback.append("FAIL: Did not mention stable keys; state may jump when dataset changes.")

        # --- E) Error handling & cancellation ---
        cancel_patterns = [
            r"CancellationException",
            r"cancel.*job",
            r"onDispose|DisposableEffect",
            r"clean.*up|cleanup",
        ]
        if self._any(cancel_patterns, llm_answer):
            score += 10
            feedback.append("SUCCESS: Mentions cancellation/cleanup strategy (important on navigation).")
        else:
            feedback.append("WARN: No explicit cancellation/cleanup strategy; may leak work across screens.")

        passed = score >= self.case.pass_score
        return {
            "test_id": self.case.test_id,
            "score": max(score, 0),
            "passed": passed,
            "feedback": feedback,
            "expected_reasoning_steps": self.case.expected_reasoning_steps,
            "grading_note": (
                "This is a heuristic grader. A human review should additionally verify Kotlin correctness and that "
                "the proposed refactor does not violate constraints."
            ),
        }

    # ---------- Internals ----------
    @staticmethod
    def _any(patterns: List[str], text: str) -> bool:
        return any(re.search(p, text, flags=re.IGNORECASE | re.DOTALL) for p in patterns)

    @staticmethod
    def _prompt() -> str:
        return (
            "ROLE: You are a Staff Android Engineer doing an architecture review.\n\n"
            "SCENARIO:\n"
            "- Chat screen supports streaming responses (up to 20 updates/sec).\n"
            "- User can switch between conversations quickly.\n"
            "- UI must stay smooth while scrolling and while streaming.\n\n"
            "SYMPTOMS FROM QA:\n"
            "1) Sometimes tokens from a previous conversation appear in a different conversation after quick switching.\n"
            "2) During streaming, the last bubble changes height frequently and the list 'jumps' / scroll feels unstable.\n"
            "3) Battery drain during idle scrolling.\n\n"
            "CONSTRAINTS:\n"
            "- You may change ONLY ChatViewModel and ChatContent.\n"
            "- Repository / interactor interfaces are frozen.\n"
            "- Provide corrected full code for these two units (may add helper functions/classes inside the same file).\n\n"
            "TASK:\n"
            "A) Identify root causes (not just symptoms).\n"
            "B) Propose an architecture fix strategy.\n"
            "C) Provide the corrected code.\n"
        )

    @staticmethod
    def _buggy_code() -> str:
        # Intentionally no inline hints.
        return r'''
// ------------ ChatViewModel.kt (BUGGY) ------------
@Immutable
data class ChatUiState(
    val conversationId: String? = null,
    val messages: List<ChatMessage> = emptyList(),
    val isStreaming: Boolean = false
)

class ChatViewModel(
    private val interactor: ILLMInteractor,
    private val conversationId: String?
) : ViewModel() {

    private val _currentConversationId = MutableStateFlow(conversationId)

    // GLOBAL buffer: messageId -> streamed tail
    private val streamingBuffer: StateFlow<Map<String, String>> =
        interactor.observeStreamingBuffer()

    val uiState: StateFlow<ChatUiState> =
        _currentConversationId.flatMapLatest { cid ->
            val historyFlow = if (cid == null) flowOf(emptyList()) else interactor.getChatHistoryFlow(cid)

            combine(historyFlow, streamingBuffer) { dbMessages, buffer ->
                val merged = dbMessages.map { msg ->
                    // merge buffer into message content on every chunk
                    msg.copy(content = msg.content + (buffer[msg.id].orEmpty()))
                }
                ChatUiState(
                    conversationId = cid,
                    messages = merged,
                    isStreaming = buffer.isNotEmpty()
                )
            }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ChatUiState())

    fun switchConversation(newId: String) {
        _currentConversationId.value = newId
    }
}


// ------------ ChatContent.kt (BUGGY) ------------
@Composable
fun ChatContent(uiState: ChatUiState) {
    val messages = uiState.messages
    val listState = rememberLazyListState()
    var userScrolledAway by remember { mutableStateOf(false) }

    val isAtBottom by remember {
        derivedStateOf {
            val layout = listState.layoutInfo
            if (layout.visibleItemsInfo.isEmpty()) true
            else layout.visibleItemsInfo.last().index >= messages.lastIndex
        }
    }

    LaunchedEffect(messages) {
        if (!userScrolledAway && messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.lastIndex)
        }
    }

    LaunchedEffect(listState.isScrollInProgress) {
        if (listState.isScrollInProgress) {
            userScrolledAway = !isAtBottom
        }
    }

    LazyColumn(state = listState) {
        items(items = messages, key = { it.id }) { msg ->
            MessageBubble(msg)
        }
    }
}
'''

# -------- Example usage --------
if __name__ == "__main__":
    test = ComposeArchitectureTest()
    print(test.get_input())
    print("\nEXPECTED:", test.get_expected_output_description())

    # Dummy answer example
    dummy = """
    // --------------------------- ChatViewModel.kt ---------------------------
@Immutable
data class ChatUiState(
    val conversationId: String? = null,
    val messages: List<ChatMessage> = emptyList(),
    val isStreaming: Boolean = false
)

class ChatViewModel(
    private val interactor: ILLMInteractor,
) : ViewModel() {

    // current conversation id – the only source of truth
    private val _currentConversationId = MutableStateFlow<String?>(null)
    val switchConversation: (String) -> Unit = { _currentConversationId.value = it }

    // UI state derived from the *selected* conversation only
    val uiState: StateFlow<ChatUiState> =
        _currentConversationId
            .flatMapLatest { cid ->
                if (cid == null) flowOf(ChatUiState())
                else buildConversationUi(cid)
            }
            .stateIn(
                viewModelScope,
                SharingStarted.Lazily,
                ChatUiState()
            )

    /**
     * Builds the UI state for a single conversation.
     *
     * * historyFlow – persisted chat history
     * * streamFlow – per‑conversation streaming flow (cancels on switch)
     */
    private fun buildConversationUi(conversationId: String): Flow<ChatUiState> {
        val historyFlow = interactor.getChatHistoryFlow(conversationId)

        // Stream only for the current conversation; cancellation happens automatically
        val streamFlow = interactor.observeStreamingForConversation(conversationId)

        return combine(historyFlow, streamFlow) { history, streamed ->
            // incremental buffer: map<msgId, String>
            val buffer = mutableMapOf<String, String>()
            streamed.forEach { (msgId, token) -> buffer.merge(msgId, token) { a, b -> a + b } }

            // merge the buffered tail into the last message of each history entry
            val mergedMessages = history.map { msg ->
                if (buffer.containsKey(msg.id)) {
                    msg.copy(content = msg.content + buffer[msg.id]!!)
                } else msg
            }
            ChatUiState(
                conversationId,
                mergedMessages,
                isStreaming = streamed.isNotEmpty()
            )
        }
    }

    /**
     * Public API used by the UI to select a new conversation.
     */
    fun switchConversation(newId: String) {
        _currentConversationId.value = newId
    }
}

// --------------------------- ChatContent.kt ---------------------------
@Composable
fun ChatContent(
    uiState: ChatUiState,
    modifier: Modifier = Modifier
) {
    val messages by rememberUpdatedState(uiState.messages)
    val listState = rememberLazyListState()

    // --- 1. Detect “at bottom” only when scrolling stops ---
    val isAtBottom by remember {
        derivedStateOf {
            with(listState.layoutInfo) {
                visibleItemsInfo.isEmpty() || lastVisibleItemIndex >= messages.lastIndex
            }
        }
    }

    // throttle UI updates to avoid layout thrashing
    LaunchedEffect(messages) {
        snapshotFlow { messages }.debounce(200).collect { newList ->
            if (!listState.isScrollInProgress && isAtBottom) {
                listState.animateScrollToItem(newList.lastIndex)
            }
        }
    }

    // --- 2. Render -----------------------------------------------
    LazyColumn(
        state = listState,
        modifier = modifier
    ) {
        items(
            items = messages,
            key = { it.id }   // stable key to avoid re‑creation of composables
        ) { msg ->
            MessageBubble(msg)
        }
    }
}

    """
    print("\n--- EVAL ---")
    print(test.evaluate(dummy))
