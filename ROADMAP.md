# Aqua Voice - Product Roadmap

## Current Version (v1.2)

### Completed Features
- [x] Menu bar app with no Dock icon
- [x] Double-tap Right Option to start recording
- [x] Single tap Right Option to stop recording
- [x] **Enter key to stop recording** (CGEventTap)
- [x] **Escape key to cancel and delete typed text** (CGEventTap)
- [x] Batch transcription with Deepgram Nova-3 (no truncation)
- [x] Final text copied to clipboard on stop
- [x] Queue-based transcript processing for reliability
- [x] Proper accessibility permission checking
- [x] Input Monitoring support for global key capture

---

## Backlog

### Priority 1: Decouple Transcription from Cursor Position
**Problem:** Currently, text is typed live at cursor position. If user scrolls or clicks elsewhere while speaking, text ends up split across multiple locations.

**Solution:**
- Buffer all transcription in memory (don't type live)
- Show visual indicator that recording is active (already have red icon)
- On stop (Enter/Option tap), paste the complete text at current cursor position
- Optionally: Show floating window with live preview of transcription

**Benefit:** User can start recording, browse/scroll freely, then place cursor and paste when ready.

**Trade-off:** Loses the "live typing" feel, but gains reliability and flexibility.

---

### Priority 2: LLM Cleanup Mode (Optional)
**Problem:** Raw Deepgram transcription has occasional errors (e.g., names misspelled, minor grammar issues).

**Solution:**
- Add toggle in menu: "Polish with AI" (off by default)
- When enabled, send final text through GPT-4o-mini or Claude for cleanup
- Only process final results (not interim) to minimize latency/cost
- Add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env

**Cost:** ~$0.001-0.01 per transcription

**Benefit:** Cleaner, more professional text output.

---

### Future Ideas
- [ ] Custom hotkey configuration
- [ ] Multiple language support
- [ ] Voice commands ("new paragraph", "delete that")
- [ ] Transcription history/log viewer
- [ ] Auto-punctuation improvements
- [ ] Integration with specific apps (Slack, email)
- [ ] Pre-built signed app for easy installation (no build required)

---

## Version History

### v1.2 (2025-12-05)
- **Enter key now works globally** using Quartz CGEventTap
- **Escape key cancels recording** and deletes typed text
- Added Input Monitoring permission requirement
- Fixed accessibility permission checking with `AXIsProcessTrustedWithOptions`
- Improved documentation with troubleshooting guide

### v1.1 (2025-12-05)
- Switched to batch transcription (interim_results=False) for reliability
- Queue-based transcript processing eliminates truncation issues
- Added Right Option single-tap to stop recording

### v1.0 (2025-12-04)
- Initial release
- Menu bar app with Deepgram Nova-3
- Double-tap Right Option hotkey
- Real-time transcription with interim results
- Escape to cancel
