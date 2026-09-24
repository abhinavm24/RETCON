(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (name) => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
  const activeStatuses = new Set(['queued', 'checking', 'rewriting']);
  const statusLabels = { queued: 'Queued', checking: 'Checking continuity', rewriting: 'Rewriting', awaiting_approval: 'Your review', published: 'Published', rejected: 'Discarded', cancelled: 'Cancelled', failed: 'Needs attention' };
  const ruleLabels = { dead_character_speaks: 'A voice from the past', dead_character_present: 'An impossible appearance', character_location_conflict: 'Two places at once', location_conflict: 'Two places at once', scene_time_backwards: 'Time runs backwards', timeline_regression: 'Time runs backwards', timestamp_regression: 'Time runs backwards' };
  let state = null;
  let selectedChapter = null;
  let currentView = 'manuscript';
  let preview = null;
  let previewBody = null;
  let busy = false;
  let dialogMode = 'import';
  let dialogChapter = null;
  let pollTimer = null;
  let toastTimer = null;
  let lastRenderKey = '';
  let hasLoaded = false;
  let pendingDecisionRun = null;
  let settings = null;
  let settingsBusy = false;
  let settingsError = '';
  let setupPrompted = false;
  const defaultModel = 'google/gemma-4-31b-it:free';
  const localModel = 'qwen3.8-27b-uncensored-mlx';
  const localBaseUrl = 'http://localhost:1234/v1';
  let settingsProvider = 'openrouter';
  let providerDrafts = {};

  async function request(path, { method = 'GET', body } = {}) {
    let response;
    try {
      response = await fetch(path, { method, headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined, body: body !== undefined ? JSON.stringify(body) : undefined, cache: 'no-store' });
    } catch (_) {
      throw new Error('The writing room is offline. Check the Airflow server connection, then try again.');
    }
    const type = response.headers.get('content-type') || '';
    const payload = type.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = payload?.detail ?? payload?.error ?? payload;
      const message = Array.isArray(detail) ? detail.map((item) => item.msg || JSON.stringify(item)).join('; ') : typeof detail === 'object' ? JSON.stringify(detail) : detail;
      throw new Error(message || `The request could not be completed (${response.status}).`);
    }
    return payload;
  }

  function toast(message, error = false) {
    clearTimeout(toastTimer);
    $('toast').textContent = message;
    $('toast').className = `toast${error ? ' error' : ''}`;
    $('toast').hidden = false;
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 7000 : 4200);
  }

  function runInProgress() {
    return Boolean(state?.run && (activeStatuses.has(state.run.status) || state.run.status === 'awaiting_approval'));
  }

  function settingsLocked() {
    return !settings || settings.editable === false || runInProgress();
  }

  function renderSettingsControls() {
    const locked = settingsLocked();
    $('settings-provider').disabled = settingsBusy || locked;
    $('settings-base-url').disabled = settingsBusy || locked;
    $('settings-model').disabled = settingsBusy || locked;
    $('settings-key').disabled = settingsBusy || locked;
    $('settings-test').disabled = settingsBusy || locked;
    $('settings-save').disabled = settingsBusy || locked;
    $('settings-close').disabled = settingsBusy;
    $('settings-save').innerHTML = `${settings?.configured ? 'Save settings' : 'Save & continue'}${icon('arrow')}`;
    $('settings-lock').hidden = !locked;
    $('settings-lock').textContent = !settings ? 'Loading your connection settings…' : runInProgress() ? 'Finish or cancel the current revision before changing its AI settings.' : 'Connection settings are managed by your Airflow administrator.';
    $('setup-banner').hidden = settings?.configured !== false;
  }

  function sameSavedConnection() {
    const provider = $('settings-provider').value;
    if (provider !== (settings?.provider || 'openrouter')) return false;
    const endpoint = (value) => String(value || '').trim().replace(/\/+$/, '');
    return provider === 'openrouter' || endpoint($('settings-base-url').value) === endpoint(settings?.base_url);
  }

  function renderProviderFields() {
    const local = $('settings-provider').value === 'openai';
    const retainedKey = sameSavedConnection() && settings?.key_present;
    $('settings-base-url-field').hidden = !local;
    $('settings-base-url').required = local;
    $('settings-model').placeholder = local ? localModel : defaultModel;
    $('settings-model-hint').textContent = local ? 'Use the model ID shown in LM Studio’s server, or your OpenAI-compatible server.' : `The demo uses ${defaultModel}. You can enter another OpenRouter model ID.`;
    $('settings-key-label').textContent = local ? 'API key (optional)' : 'OpenRouter API key';
    $('settings-key').required = !local && !retainedKey;
    $('settings-key').placeholder = retainedKey ? 'Leave blank to keep the saved key' : local ? 'Leave blank if your server needs no key' : 'Paste your OpenRouter key';
    $('settings-key-hint').textContent = retainedKey ? 'A key is saved for this connection. Leave blank to keep it, or paste a replacement.' : local ? 'LM Studio normally needs no key. Add one only if your server requires it.' : 'Your key is sent to this workspace’s server and stored in Airflow.';
    const configured = sameSavedConnection() && settings?.configured;
    $('settings-connection').textContent = configured ? 'Configured' : 'Setup needed';
    $('settings-connection').classList.toggle('configured', Boolean(configured));
  }

  function fillSettings() {
    settingsProvider = settings?.provider === 'openai' ? 'openai' : 'openrouter';
    providerDrafts = {};
    $('settings-provider').value = settingsProvider;
    $('settings-model').value = settings?.model || (settingsProvider === 'openai' ? localModel : defaultModel);
    $('settings-base-url').value = settings?.base_url || settings?.default_base_url || localBaseUrl;
    $('settings-key').value = '';
    $('settings-title').textContent = settings?.configured ? 'AI settings' : 'Meet your writing assistant';
    $('settings-description').textContent = settings?.configured ? 'Choose the model that helps repair your story. You stay in control of every revision.' : 'Choose OpenRouter or a local model, then start with the demo or bring your own draft.';
    renderProviderFields();
    renderSettingsControls();
  }

  function changeProvider() {
    providerDrafts[settingsProvider] = { model: $('settings-model').value, baseUrl: $('settings-base-url').value };
    settingsProvider = $('settings-provider').value;
    const draft = providerDrafts[settingsProvider];
    $('settings-model').value = draft?.model ?? (settingsProvider === 'openai' ? localModel : defaultModel);
    $('settings-base-url').value = draft?.baseUrl ?? settings?.default_base_url ?? localBaseUrl;
    // A typed credential belongs to its original endpoint, never the new one.
    $('settings-key').value = '';
    renderProviderFields();
    settingsFeedback('');
  }

  function settingsFeedback(message, kind = 'error') {
    // Never display the submitted key, even if an upstream error includes it.
    const candidateKey = $('settings-key').value.trim();
    let safeMessage = String(message || '');
    if (candidateKey) safeMessage = safeMessage.split(candidateKey).join('[redacted]');
    safeMessage = safeMessage.replace(/sk-or-[a-zA-Z0-9_-]+/g, '[redacted]');
    $('settings-feedback').textContent = safeMessage;
    $('settings-feedback').className = `settings-feedback ${kind}`;
    $('settings-feedback').hidden = !safeMessage;
  }

  async function loadSettings({ prompt = false } = {}) {
    try {
      settings = await request('api/settings');
      settingsError = '';
      renderSettingsControls();
      if (prompt && !settings.configured && !setupPrompted && !document.querySelector('dialog[open]')) {
        setupPrompted = true;
        fillSettings();
        settingsFeedback('');
        $('settings-dialog').showModal();
      }
      return true;
    } catch (error) {
      settingsError = error.message;
      return false;
    }
  }

  async function openSettings() {
    if (settingsBusy) return;
    if ($('settings-dialog').open) return;
    fillSettings();
    settingsFeedback('');
    if (!$('settings-dialog').open) $('settings-dialog').showModal();
    settingsBusy = true;
    renderSettingsControls();
    await loadSettings();
    settingsBusy = false;
    fillSettings();
    if (settingsError) settingsFeedback(settingsError);
  }

  function settingsBody() {
    renderProviderFields();
    if (!$('settings-form').reportValidity()) return null;
    const provider = $('settings-provider').value;
    const model = $('settings-model').value.trim();
    const baseUrl = $('settings-base-url').value.trim();
    const key = $('settings-key').value.trim();
    if (!model) { settingsFeedback('Enter a model ID.'); return null; }
    if (provider === 'openai' && !baseUrl) { settingsFeedback('Enter your server’s API base URL.'); return null; }
    if (provider === 'openrouter' && !key && !(sameSavedConnection() && settings?.key_present)) { settingsFeedback('Add an OpenRouter API key to connect your model.'); return null; }
    return { provider, model, ...(provider === 'openai' ? { base_url: baseUrl } : {}), ...(key ? { api_key: key } : {}) };
  }

  async function testSettings() {
    if (settingsBusy || settingsLocked()) return;
    const body = settingsBody();
    if (!body) return;
    settingsBusy = true;
    renderSettingsControls();
    $('settings-test').innerHTML = `${icon('clock')}Testing…`;
    settingsFeedback('Asking your selected model for a short response…', 'pending');
    try {
      const result = await request('api/settings/test', { method: 'POST', body });
      settingsFeedback(result.ok ? 'Connection works. Save your settings to use this model for revisions.' : (result.message || 'The model could not complete the test. Check your model ID, server URL, and key.'), result.ok ? 'success' : 'error');
    } catch (error) { settingsFeedback(error.message); }
    finally {
      settingsBusy = false;
      $('settings-test').innerHTML = `${icon('check')}Test connection`;
      renderSettingsControls();
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    if (settingsBusy || settingsLocked()) return;
    const body = settingsBody();
    if (!body) return;
    settingsBusy = true;
    renderSettingsControls();
    $('settings-save').innerHTML = `${icon('clock')}Saving…`;
    settingsFeedback('');
    try {
      settings = await request('api/settings', { method: 'PUT', body });
      $('settings-key').value = '';
      $('settings-dialog').close();
      toast('Writing assistant connected. Your next revision will use the saved model.');
      await loadState();
    } catch (error) { settingsFeedback(error.message); }
    finally { settingsBusy = false; renderSettingsControls(); }
  }

  function effectiveReport() {
    return preview || state?.run || null;
  }

  function chapterById(id) {
    return state?.story?.chapters?.find((chapter) => String(chapter.id) === String(id));
  }

  function numberList(items) {
    return (items || []).map((item) => typeof item === 'object' ? item.chapter_id ?? item.id : item);
  }

  function containsChapter(items, id) {
    return numberList(items).some((item) => String(item) === String(id));
  }

  function issueList(report = effectiveReport()) {
    return Array.isArray(report?.issues) ? report.issues : [];
  }

  function wordCount(text) {
    return String(text ?? '').trim().split(/\s+/).filter(Boolean).length;
  }

  function safeAirflowUrl(raw) {
    if (!raw) return null;
    try {
      const url = new URL(raw, location.href);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
    } catch (_) { return null; }
  }

  function renderControls() {
    const locked = busy || runInProgress();
    $('preview-button').disabled = locked || !state?.story?.characters?.length || !state?.story?.chapters?.length;
    $('character-input').disabled = locked;
    $('chapter-input').disabled = locked;
    $('instruction-input').disabled = locked;
    $('edit-button').disabled = locked || !selectedChapter;
    $('import-button').disabled = locked;
    $('reset-button').disabled = busy || runInProgress();
    if (!busy) $('preview-button').innerHTML = `${icon('branch')}<span>${runInProgress() ? 'Revision in progress' : 'Inspect the ripple'}</span>${icon('arrow').replace('<svg ', '<svg class="button-arrow" ')}`;
    renderSettingsControls();
  }

  function populateInputs() {
    const characters = state?.story?.characters || [];
    const chapters = state?.story?.chapters || [];
    const previousCharacter = $('character-input').value;
    const previousChapter = $('chapter-input').value;
    const characterKey = characters.map((character) => `${character.id}:${character.name}`).join('|');
    if ($('character-input').dataset.options !== characterKey) {
      $('character-input').innerHTML = characters.map((character) => `<option value="${esc(character.id)}">${esc(character.name)}</option>`).join('');
      if (characters.some((character) => String(character.id) === previousCharacter)) $('character-input').value = previousCharacter;
      $('character-input').dataset.options = characterKey;
    }
    const chapterKey = chapters.map((chapter) => chapter.id).join('|');
    if ($('chapter-input').dataset.options !== chapterKey) {
      $('chapter-input').innerHTML = chapters.map((chapter) => `<option value="${esc(chapter.id)}">Chapter ${esc(chapter.id)}</option>`).join('');
      if (chapters.some((chapter) => String(chapter.id) === previousChapter)) $('chapter-input').value = previousChapter;
      $('chapter-input').dataset.options = chapterKey;
    }
    $('preview-button').disabled = !characters.length || !chapters.length;
  }

  function renderHeader() {
    const story = state.story;
    const engine = state.engine || {};
    const words = story.chapters.reduce((total, chapter) => total + (chapter.paragraphs || []).reduce((sum, paragraph) => sum + wordCount(paragraph.text), 0), 0);
    $('sidebar-title').textContent = story.title || 'Untitled manuscript';
    $('sidebar-subtitle').textContent = story.subtitle || 'A story in motion';
    $('breadcrumb-title').textContent = story.title || 'Manuscript';
    $('chapter-count').textContent = String(story.chapters.length).padStart(2, '0');
    $('manuscript-version').textContent = `MANUSCRIPT v${story.version ?? 1}`;
    document.title = `${story.title || 'Your manuscript'} — RETCON`;
    $('engine-badge').className = `engine-badge${engine.available === false ? ' unavailable' : ''}`;
    $('engine-badge').innerHTML = `<span class="status-dot"></span>Airflow plugin${engine.available === false ? ' · unavailable' : ''}`;
    $('engine-badge').title = `This writing room runs inside Apache Airflow.${engine.model ? ` Model: ${engine.model}.` : ''}`;
    const run = state.run;
    const report = effectiveReport();
    const issues = issueList(report);
    const published = !preview && run?.status === 'published';
    let heading = 'Your story, ready for its next twist';
    let subheading = 'Inspect a change to discover which chapters it affects';
    let attention = false;
    if (preview) {
      heading = `${issues.length} continuity ${issues.length === 1 ? 'issue' : 'issues'} found in this twist`;
      subheading = 'Preview only · your manuscript has not changed';
      attention = issues.length > 0;
    } else if (activeStatuses.has(run?.status)) {
      heading = statusLabels[run.status];
      subheading = 'Your current manuscript stays intact while we prepare a revision';
      attention = true;
    } else if (run?.status === 'awaiting_approval') {
      heading = 'The next version is ready for your review';
      subheading = 'Compare the changes, then decide what becomes canon';
      attention = true;
    } else if (published) {
      heading = 'Your revision is published.';
      subheading = `${run.metrics?.rewritten ?? (run.patches || []).length} ${Number(run.metrics?.rewritten ?? (run.patches || []).length) === 1 ? 'chapter' : 'chapters'} revised · approved by you`;
    } else if (run?.status === 'failed') {
      heading = 'This revision needs attention';
      subheading = 'Your saved manuscript is intact. See the activity details below.';
      attention = true;
    } else if (['rejected', 'cancelled'].includes(run?.status)) {
      heading = 'Back to the story you chose';
      subheading = 'The proposed revision was discarded. Try another twist whenever you’re ready.';
    }
    $('story-health').className = `story-health${attention ? ' attention' : ''}`;
    $('story-health').innerHTML = `<div><span class="health-symbol">${icon(attention ? 'branch' : 'shield')}</span><span><strong>${esc(heading)}</strong><small>${esc(subheading)}</small></span></div><div class="health-stats"><span><strong>${story.chapters.length}</strong> chapters</span><span><strong>${words.toLocaleString()}</strong> words</span><span class="health-fact-count"><strong>${story.characters.length}</strong> characters</span></div>`;
    const href = safeAirflowUrl(run?.airflow_url);
    $('airflow-link').hidden = !href;
    if (href) $('airflow-link').href = href;
  }

  function renderChapterNav() {
    const report = effectiveReport();
    const issues = issueList(report);
    const run = state.run;
    const patches = report?.patches || [];
    $('chapter-nav').innerHTML = state.story.chapters.map((chapter) => {
      const hasIssue = issues.some((issue) => String(issue.chapter_id) === String(chapter.id)) && (preview || !['published', 'rejected', 'cancelled'].includes(run?.status));
      const working = !preview && activeStatuses.has(run?.status) && containsChapter(run.affected, chapter.id);
      const changed = !preview && run?.status === 'published' && patches.some((patch) => String(patch.chapter_id) === String(chapter.id));
      const dot = working ? 'working' : hasIssue ? 'issue' : changed ? 'changed' : '';
      const hint = working ? 'Being checked' : hasIssue ? 'Continuity issue found' : changed ? 'Revised' : 'Saved chapter';
      return `<button class="chapter-item${String(selectedChapter) === String(chapter.id) ? ' active' : ''}" data-chapter="${esc(chapter.id)}" ${String(selectedChapter) === String(chapter.id) ? 'aria-current="page"' : ''} title="${esc(chapter.title)} · ${hint}"><span class="chapter-number">${String(chapter.id).padStart(2, '0')}</span><span class="chapter-item-title">${esc(chapter.title)}</span><span class="chapter-dot ${dot}" aria-label="${hint}"></span></button>`;
    }).join('');
  }

  function renderBible() {
    $('character-bible').innerHTML = state.story.characters.map((character, index) => {
      const dead = character.death_chapter != null || character.status === 'dead';
      const description = character.role || character.description || (dead ? `Dies at the end of chapter ${character.death_chapter ?? '?'}` : 'Part of the story’s canon');
      return `<div class="character-row"><span class="character-avatar tint-${index % 4}">${esc(character.name?.charAt(0) || '?')}</span><div class="character-details"><div class="character-name">${esc(character.name)}</div><div class="character-description">${esc(description)}</div></div><span class="character-status${dead ? ' dead' : ''}"><span class="status-dot"></span>${dead ? 'Deceased' : esc(character.status || 'Alive').replace(/^./, (c) => c.toUpperCase())}</span></div>`;
    }).join('') || '<p class="bible-description">No characters have been indexed yet.</p>';
  }

  function renderManuscript() {
    const chapter = chapterById(selectedChapter);
    if (!chapter) return `<div class="empty-state">${icon('book')}<h2>A world waiting to be written.</h2><p>Bring a draft into your writing room to get started.</p></div>`;
    const allIssues = issueList();
    const issuesVisible = preview || !['published', 'rejected', 'cancelled'].includes(state.run?.status);
    const chapterIssues = issuesVisible ? allIssues.filter((issue) => String(issue.chapter_id) === String(chapter.id)) : [];
    const paragraphs = chapter.paragraphs || [];
    const words = paragraphs.reduce((total, paragraph) => total + wordCount(paragraph.text), 0);
    const index = state.story.chapters.indexOf(chapter);
    const previous = state.story.chapters[index - 1];
    const next = state.story.chapters[index + 1];
    const firstLocation = paragraphs.find((paragraph) => paragraph.location)?.location;
    const stateText = chapterIssues.length ? `${chapterIssues.length} ${chapterIssues.length === 1 ? 'issue' : 'issues'} to resolve` : state.run?.status === 'published' && (state.run.patches || []).some((patch) => String(patch.chapter_id) === String(chapter.id)) ? 'Revision approved' : 'Saved manuscript';
    return `<article class="chapter-content"><div class="chapter-kicker"><span>CHAPTER ${String(chapter.id).padStart(2, '0')}</span><span class="chapter-state${chapterIssues.length ? ' issue' : ''}"><span class="status-dot"></span>${esc(stateText)}</span></div><h2>${esc(chapter.title)}</h2><div class="chapter-meta">${icon('clock')} ${Math.max(1, Math.ceil(words / 220))} min read<span>·</span>${words} words${firstLocation ? `<span>·</span>${esc(firstLocation).replaceAll('_', ' ')}` : ''}</div><div class="chapter-rule"></div>${paragraphs.map((paragraph) => {
      const paragraphIssues = chapterIssues.filter((issue) => String(issue.paragraph_id) === String(paragraph.id));
      return `<p class="prose${paragraphIssues.length ? ' issue-paragraph' : ''}" id="paragraph-${esc(paragraph.id)}">${esc(paragraph.text).replaceAll('\n', '<br>')}${paragraphIssues.length ? `<span class="paragraph-annotation">${icon('shield')}${esc(ruleLabels[paragraphIssues[0].rule] || paragraphIssues[0].rule.replaceAll('_', ' '))}</span>` : ''}</p>`;
    }).join('')}<div class="chapter-end">· · ·</div><div class="chapter-next">${previous ? `<button class="text-button previous" data-chapter="${esc(previous.id)}">${icon('arrow')}Chapter ${esc(previous.id)}</button>` : '<span></span>'}${next ? `<button class="text-button" data-chapter="${esc(next.id)}">Chapter ${esc(next.id)}: ${esc(next.title)}${icon('arrow')}</button>` : '<span class="text-button">For now, the end.</span>'}</div></article>`;
  }

  function renderContinuity() {
    const report = effectiveReport();
    if (!report) return `<div class="empty-state">${icon('shield')}<h2>Every fact leaves a footprint.</h2><p>Inspect a twist to see which chapters depend on it, and where the story would break.</p></div>`;
    const issues = issueList(report);
    const published = !preview && state.run?.status === 'published';
    const rejected = !preview && ['rejected', 'cancelled'].includes(state.run?.status);
    const chapters = state.story.chapters;
    return `<div class="view-content"><div class="view-heading"><div class="eyebrow">${preview ? 'BEFORE YOU COMMIT' : published ? 'THE REVISION RECORD' : 'FOLLOW THE CONSEQUENCES'}</div><h2>${published ? 'The breaks we repaired.' : rejected ? 'A future you discarded.' : 'Where the story changes.'}</h2><p>${published ? 'These violations were found in the previous draft and resolved in your approved revision.' : rejected ? 'These findings belonged to the discarded twist. Your manuscript was kept as it was.' : `${numberList(report.affected).length} chapters in the affected path. We only rewrite paragraphs that need repair.`}</p></div><div class="scan-map">${chapters.map((chapter) => `<button class="chapter-chip${containsChapter(report.affected, chapter.id) ? ' affected' : ''}" data-chapter="${esc(chapter.id)}" style="border:0">${icon(containsChapter(report.affected, chapter.id) ? 'branch' : 'check')}Ch. ${esc(chapter.id)}</button>`).join('')}</div>${issues.length ? issues.map((issue) => `<div class="issue-card"><div class="issue-card-head"><span class="issue-rule">${esc(issue.rule).replaceAll('_', ' ')}</span><span>CHAPTER ${esc(issue.chapter_id)}</span></div><div class="issue-card-body"><h3>${esc(issue.message || ruleLabels[issue.rule] || 'Continuity conflict')}</h3><blockquote>${esc(issue.quote || 'No quoted text was provided.')}</blockquote><button class="text-button" data-chapter="${esc(issue.chapter_id)}" data-paragraph="${esc(issue.paragraph_id)}">Read in context${icon('arrow')}</button></div></div>`).join('') : `<div class="clean-notice">${icon('check')}<span>${activeStatuses.has(state.run?.status) && !preview ? 'Continuity checks are running. Findings will appear here.' : 'No continuity violations found by the current checks.'}</span></div>`}</div>`;
  }

  // Highlight the changed span without inserting untrusted prose as HTML.
  function diffText(before, after) {
    const a = String(before ?? '').split(/(\s+)/);
    const b = String(after ?? '').split(/(\s+)/);
    let start = 0;
    while (start < Math.min(a.length, b.length) && a[start] === b[start]) start++;
    let end = 0;
    while (end < Math.min(a.length - start, b.length - start) && a[a.length - 1 - end] === b[b.length - 1 - end]) end++;
    const highlight = (words) => `${esc(words.slice(0, start).join(''))}${words.length - end > start ? `<mark>${esc(words.slice(start, end ? -end : undefined).join(''))}</mark>` : ''}${end ? esc(words.slice(-end).join('')) : ''}`;
    return [highlight(a), highlight(b)];
  }

  function renderChanges() {
    const run = state.run;
    const patches = run?.patches || [];
    if (!patches.length) return `<div class="empty-state">${icon('branch')}<h2>Make room for another version.</h2><p>${run?.status === 'rewriting' ? 'Your revision is being prepared. Paragraph comparisons will appear as they become available.' : 'When a twist needs a rewrite, compare every changed paragraph here before you approve it.'}</p></div>`;
    const published = run.status === 'published';
    const rejected = ['rejected', 'cancelled'].includes(run.status);
    const failed = run.status === 'failed';
    const uniqueChapters = new Set(patches.map((patch) => patch.chapter_id)).size;
    return `<div class="view-content"><div class="view-heading"><div class="eyebrow">${published ? 'YOUR APPROVED REVISION' : rejected ? 'DISCARDED REVISION' : failed ? 'REVISION STOPPED' : 'YOU HAVE THE FINAL SAY'}</div><h2>${published ? 'A different story. Still yours.' : rejected ? 'The road not taken.' : failed ? 'An unfinished possibility.' : 'Small edits. A new reality.'}</h2><p>${published ? 'These changes are now part of your manuscript.' : rejected ? 'These changes were discarded. They are shown here for your reference.' : failed ? 'The revision stopped before publication. These partial outputs are shown for inspection; your saved story is intact.' : 'Your original draft is safe. Review the proposed changes before they become part of your story.'}</p></div><div class="change-summary"><strong>${patches.length} ${patches.length === 1 ? 'paragraph' : 'paragraphs'}</strong> across <strong>${uniqueChapters} ${uniqueChapters === 1 ? 'chapter' : 'chapters'}</strong>. ${esc(run.metrics?.untouched ?? 0)} chapters untouched.</div>${patches.map((patch) => {
      const [before, after] = diffText(patch.before, patch.after);
      const chapter = chapterById(patch.chapter_id);
      return `<section class="diff-card"><div class="diff-card-head"><span class="diff-chapter-name">Chapter ${esc(patch.chapter_id)}${chapter ? ` · ${esc(chapter.title)}` : ''}</span><span>${esc(patch.paragraph_id)}</span></div><div class="diff-grid"><div class="diff-side before"><div class="diff-label">− ORIGINAL</div><p>${before}</p></div><div class="diff-side after"><div class="diff-label">+ ${published ? 'APPROVED' : 'PROPOSED'}</div><p>${after}</p></div></div><div class="diff-reason">${icon('spark').replace('<svg ', '<svg style="width:10px;height:10px;vertical-align:middle;margin-right:4px" ')}${esc(patch.reason || 'Updated to preserve story continuity.')}</div></section>`;
    }).join('')}</div>`;
  }

  function renderDocument(force = false) {
    if (!state) return;
    const report = effectiveReport();
    const key = JSON.stringify([currentView, selectedChapter, state.story, report, state.run?.patches, state.run?.status]);
    if (force || key !== lastRenderKey) {
      $('document-view').innerHTML = currentView === 'manuscript' ? renderManuscript() : currentView === 'continuity' ? renderContinuity() : renderChanges();
      lastRenderKey = key;
    }
    document.querySelectorAll('.view-tab').forEach((button) => {
      const active = button.dataset.view === currentView;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });
    const issues = issueList(report).length;
    $('issue-count').hidden = !issues;
    $('issue-count').textContent = issues;
    const patches = state.run?.patches?.length || 0;
    $('patch-count').hidden = !patches;
    $('patch-count').textContent = patches;
    $('edit-button').hidden = currentView !== 'manuscript';
    $('document-status').textContent = currentView === 'manuscript' ? (state.run?.status === 'awaiting_approval' ? 'Original draft · revision awaiting approval' : 'Saved in your workspace') : currentView === 'continuity' ? (preview ? 'Impact preview · no changes saved' : 'Continuity audit') : (state.run?.status === 'published' ? 'Revision published' : 'Proposed revision');
    const index = state.story.chapters.findIndex((chapter) => String(chapter.id) === String(selectedChapter));
    $('document-position').textContent = currentView === 'manuscript' && index >= 0 ? `${String(index + 1).padStart(2, '0')} / ${String(state.story.chapters.length).padStart(2, '0')}` : '';
  }

  function renderPreview() {
    const host = $('impact-preview');
    host.hidden = !preview;
    if (!preview) return;
    const affected = numberList(preview.affected);
    const unchanged = numberList(preview.unchanged);
    const issues = issueList(preview);
    host.innerHTML = `<div class="impact-preview"><div class="impact-kicker">${icon('branch')}THE RIPPLE, BEFORE THE REWRITE</div><h3>${affected.length ? `${affected.length} ${affected.length === 1 ? 'chapter feels' : 'chapters feel'} this change.` : 'No downstream chapters are affected.'}</h3><div class="impact-chapters">${state.story.chapters.map((chapter) => `<span class="chapter-chip${containsChapter(affected, chapter.id) ? ' affected' : ''}">${icon(containsChapter(affected, chapter.id) ? 'branch' : 'check')}Ch. ${esc(chapter.id)}</span>`).join('')}</div><p class="impact-summary">${issues.length} ${issues.length === 1 ? 'continuity issue' : 'continuity issues'} found. ${unchanged.length} ${unchanged.length === 1 ? 'chapter stays' : 'chapters stay'} untouched. Only broken paragraphs will be rewritten; you’ll approve the result.</p><button type="button" class="primary-button apply-button" id="apply-button" ${busy || runInProgress() ? 'disabled' : ''}>${icon('spark')}Apply twist & prepare revision${icon('arrow')}</button></div>`;
  }

  function displayTime(time) {
    if (!time) return '';
    const value = new Date(time);
    return Number.isNaN(value.getTime()) ? '' : value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function renderRun() {
    const host = $('run-panel');
    const run = state.run;
    host.hidden = !run;
    if (!run) return;
    const active = activeStatuses.has(run.status);
    const events = Array.isArray(run.events) ? run.events : [];
    const metrics = run.metrics || {};
    const descriptions = { queued: 'Your twist is queued. The original manuscript remains safe.', checking: 'Checking existing prose against the new story facts.', rewriting: 'Repairing affected paragraphs and checking the result.', awaiting_approval: 'The revision is prepared. Your approval makes it canon.', published: 'Your revision is now part of the manuscript.', rejected: 'Revision discarded. Your original story is unchanged.', cancelled: 'Revision cancelled. Your original story is unchanged.', failed: 'The revision could not finish. Your saved manuscript is intact.' };
    const href = safeAirflowUrl(run.airflow_url);
    host.innerHTML = `<div class="run-header"><h2>The ripple in motion</h2><span class="run-status${active ? ' active' : ''}${run.status === 'failed' ? ' failed' : ''}"><span class="status-dot"></span>${esc(statusLabels[run.status] || run.status)}</span></div><p class="run-summary">${esc(descriptions[run.status] || 'Tracking the revision.')}</p><div class="run-metrics"><div><strong>${esc(metrics.checked ?? 0)}</strong>CHECKED</div><div><strong>${esc(metrics.rewritten ?? 0)}</strong>REWRITTEN</div><div><strong>${esc(metrics.untouched ?? 0)}</strong>UNTOUCHED</div></div>${run.status === 'awaiting_approval' ? `<div class="decision-card"><strong>${pendingDecisionRun === run.id ? 'Your decision is being saved.' : 'Does this feel like your story?'}</strong><p>Review the paragraph changes, then accept the revision or keep your current draft.</p><button class="run-detail-link" data-view="changes" style="margin:0 0 12px">Compare the changes${icon('arrow')}</button><div class="decision-buttons"><button class="secondary-button" data-decision="reject" ${busy || pendingDecisionRun === run.id ? 'disabled' : ''}>Keep original</button><button class="primary-button" data-decision="approve" ${busy || pendingDecisionRun === run.id ? 'disabled' : ''}>${icon('check')}Approve revision</button></div></div>` : ''}${active || run.status === 'awaiting_approval' ? `<button type="button" class="run-detail-link" data-cancel-run ${busy ? 'disabled' : ''}>Cancel revision · keep original</button>` : ''}${run.error ? `<div class="inline-error">${esc(typeof run.error === 'string' ? run.error : JSON.stringify(run.error))}</div>` : ''}${events.length ? `<div class="activity-title">ACTIVITY</div><div class="activity-feed">${events.slice(-8).reverse().map((event) => `<div class="activity-item${['error', 'failed', 'violation'].includes(event.kind) ? ' error' : ''}"><span class="activity-dot"></span><span>${esc(event.message)}</span><time>${esc(displayTime(event.time))}</time></div>`).join('')}</div>` : ''}${href ? `<a class="run-detail-link" href="${esc(href)}" target="_blank" rel="noreferrer">See the Airflow run${icon('external')}</a>` : ''}`;
  }

  function render() {
    if (!state?.story) return;
    if (!chapterById(selectedChapter)) selectedChapter = state.story.chapters[0]?.id ?? null;
    populateInputs();
    renderHeader();
    renderChapterNav();
    renderBible();
    renderDocument();
    renderPreview();
    renderRun();
    renderControls();
  }

  async function loadState() {
    clearTimeout(pollTimer);
    try {
      const incoming = await request('api/state');
      if (!incoming?.story || !Array.isArray(incoming.story.chapters)) throw new Error('The server returned an incomplete workspace. Please restart the server and try again.');
      const previousStatus = state?.run?.status;
      const previousRun = state?.run?.id;
      state = incoming;
      if (pendingDecisionRun && (state.run?.id !== pendingDecisionRun || state.run?.status !== 'awaiting_approval')) pendingDecisionRun = null;
      $('connection-error').hidden = true;
      if (hasLoaded && state.run?.status === 'awaiting_approval' && (previousStatus !== 'awaiting_approval' || previousRun !== state.run.id)) {
        currentView = 'changes';
        toast('Your revision is ready. Review the changes and make the final call.');
      }
      hasLoaded = true;
      render();
    } catch (error) {
      $('connection-error').textContent = error.message;
      $('connection-error').hidden = false;
      if (!hasLoaded) {
        $('engine-badge').className = 'engine-badge unavailable';
        $('engine-badge').innerHTML = '<span class="status-dot"></span>Airflow plugin · unavailable';
        $('engine-badge').title = 'The Airflow server connection is unavailable.';
        $('preview-button').disabled = true;
        $('edit-button').disabled = true;
      }
    } finally {
      pollTimer = setTimeout(loadState, activeStatuses.has(state?.run?.status) || state?.run?.status === 'awaiting_approval' ? 1500 : 6000);
    }
  }

  function formBody() {
    return { character_id: $('character-input').value, death_chapter: Number($('chapter-input').value), instruction: $('instruction-input').value.trim() };
  }

  async function inspect(event) {
    event.preventDefault();
    if (busy || runInProgress() || !state) return;
    busy = true;
    $('form-error').hidden = true;
    $('preview-button').innerHTML = `${icon('branch')}<span>Tracing the consequences…</span>`;
    renderControls();
    try {
      const body = formBody();
      if (!body.instruction) throw new Error('Add a twist so we know what you want to change.');
      preview = await request('api/retcons/preview', { method: 'POST', body });
      previewBody = body;
      currentView = 'continuity';
      render();
      if (window.innerWidth < 961) $('impact-preview').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (error) {
      $('form-error').textContent = error.message;
      $('form-error').hidden = false;
    } finally {
      busy = false;
      renderControls();
      renderPreview();
    }
  }

  async function applyRetcon() {
    if (!preview || !previewBody || busy || runInProgress()) return;
    if (!settings?.configured) { await openSettings(); return; }
    busy = true;
    renderControls();
    const button = $('apply-button');
    if (button) { button.disabled = true; button.textContent = 'Starting your revision…'; }
    try {
      const result = await request('api/retcons', { method: 'POST', body: previewBody });
      preview = null;
      previewBody = null;
      if (result?.id) state.run = result;
      await loadState();
      $('run-panel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (error) {
      $('form-error').textContent = error.message;
      $('form-error').hidden = false;
    } finally {
      busy = false;
      render();
    }
  }

  async function cancelRevision() {
    if (!state?.run?.id || busy) return;
    busy = true;
    renderRun();
    try {
      await request(`api/runs/${encodeURIComponent(state.run.id)}/cancel`, { method: 'POST', body: {} });
      pendingDecisionRun = null;
      await loadState();
      toast('Revision cancelled. Your saved manuscript is unchanged.');
    } catch (error) {
      toast(error.message, true);
    } finally {
      busy = false;
      render();
    }
  }

  async function decide(approved) {
    if (!state?.run?.id || busy || state.run.status !== 'awaiting_approval') return;
    busy = true;
    renderControls();
    renderRun();
    try {
      const result = await request(`api/runs/${encodeURIComponent(state.run.id)}/decision`, { method: 'POST', body: { approved } });
      if (result?.status === 'decision_submitted') pendingDecisionRun = state.run.id;
      await loadState();
      toast(result?.status === 'decision_submitted' ? 'Decision sent. Waiting for the saved manuscript to update.' : approved ? 'Revision approved. This is your story now.' : 'Original manuscript kept. There’s always another twist.');
    } catch (error) { toast(error.message, true); }
    finally { busy = false; render(); }
  }

  function setView(view) {
    if (!['manuscript', 'continuity', 'changes'].includes(view)) return;
    currentView = view;
    renderDocument(true);
  }

  function selectChapter(id, paragraphId) {
    const chapter = chapterById(id);
    if (!chapter) return;
    selectedChapter = chapter.id;
    currentView = 'manuscript';
    renderChapterNav();
    renderDocument(true);
    if (paragraphId) document.getElementById(`paragraph-${paragraphId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    else if (window.innerWidth < 961) $('document-view').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function openDraft(mode) {
    if (runInProgress() || busy) return;
    dialogMode = mode;
    dialogChapter = mode === 'edit' ? chapterById(selectedChapter) : null;
    if (mode === 'edit' && !dialogChapter) return;
    $('dialog-title').textContent = mode === 'edit' ? `Edit chapter ${dialogChapter.id}` : 'Bring your own draft';
    $('dialog-eyebrow').textContent = mode === 'edit' ? 'EVERY WORD IS YOURS' : 'A NEW STORY BEGINS';
    $('dialog-description').textContent = mode === 'edit' ? 'Shape the prose in your own voice. Separate paragraphs with a blank line.' : 'Paste a draft or upload a text file with Chapter 1 / Chapter 2 headings. Characters are indexed from explicit dialogue attributions; scene location and time are not inferred.';
    $('draft-title-label').firstChild.textContent = mode === 'edit' ? 'Chapter title' : 'Story title';
    $('draft-title').value = mode === 'edit' ? dialogChapter.title : '';
    $('draft-text').value = mode === 'edit' ? (dialogChapter.paragraphs || []).map((paragraph) => paragraph.text).join('\n\n') : '';
    $('draft-save').innerHTML = `${mode === 'edit' ? 'Save chapter' : 'Open in RETCON'}${icon('arrow')}`;
    $('upload-area').hidden = mode === 'edit';
    $('draft-hint').textContent = mode === 'edit' ? 'Saving updates this chapter. Characters use explicit dialogue attribution; scene location and time are not inferred.' : 'Import replaces this workspace’s manuscript. Export your current draft first if you’d like to keep it.';
    $('draft-error').hidden = true;
    $('file-name').textContent = '';
    $('draft-file').value = '';
    $('draft-dialog').showModal();
  }

  async function saveDraft(event) {
    event.preventDefault();
    if (busy) return;
    busy = true;
    $('draft-save').disabled = true;
    $('draft-save').textContent = 'Saving your words…';
    $('draft-error').hidden = true;
    try {
      const body = { title: $('draft-title').value.trim(), text: $('draft-text').value.trim() };
      if (!body.text || !body.title) throw new Error('Add a title and some prose before saving.');
      await request(dialogMode === 'edit' ? `api/chapters/${encodeURIComponent(dialogChapter.id)}` : 'api/import', { method: dialogMode === 'edit' ? 'PUT' : 'POST', body });
      preview = null;
      previewBody = null;
      currentView = 'manuscript';
      if (dialogMode === 'import') selectedChapter = null;
      await loadState();
      $('draft-dialog').close();
      toast(dialogMode === 'edit' ? 'Chapter saved. Keep the story moving.' : 'Your draft has a new home. Welcome to the writing room.');
    } catch (error) {
      $('draft-error').textContent = error.message;
      $('draft-error').hidden = false;
    } finally {
      busy = false;
      $('draft-save').disabled = false;
      $('draft-save').innerHTML = `${dialogMode === 'edit' ? 'Save chapter' : 'Open in RETCON'}${icon('arrow')}`;
      renderControls();
    }
  }

  async function resetDemo() {
    if (busy || runInProgress()) return;
    busy = true;
    $('reset-confirm').disabled = true;
    try {
      await request('api/reset', { method: 'POST', body: {} });
      preview = null;
      previewBody = null;
      selectedChapter = null;
      currentView = 'manuscript';
      $('character-input').value = 'mara';
      $('chapter-input').value = '2';
      $('instruction-input').value = 'Mara betrays the crew and dies at the end of chapter 2.';
      await loadState();
      $('reset-dialog').close();
      toast('Back to the beginning. Aster is ready for another twist.');
    } catch (error) { toast(error.message, true); }
    finally { busy = false; $('reset-confirm').disabled = false; render(); }
  }

  document.addEventListener('click', (event) => {
    const chapter = event.target.closest('[data-chapter]');
    if (chapter) { selectChapter(chapter.dataset.chapter, chapter.dataset.paragraph); return; }
    const view = event.target.closest('[data-view]');
    if (view) { setView(view.dataset.view); return; }
    if (event.target.closest('[data-cancel-run]')) { cancelRevision(); return; }
    const decision = event.target.closest('[data-decision]');
    if (decision) { decide(decision.dataset.decision === 'approve'); return; }
    if (event.target.closest('#apply-button')) applyRetcon();
  });
  $('retcon-form').addEventListener('submit', inspect);
  ['character-input', 'chapter-input', 'instruction-input'].forEach((id) => $(id).addEventListener('input', () => {
    if (preview) { preview = null; previewBody = null; render(); }
    $('form-error').hidden = true;
  }));
  $('import-button').addEventListener('click', () => openDraft('import'));
  $('edit-button').addEventListener('click', () => openDraft('edit'));
  $('dialog-close').addEventListener('click', () => $('draft-dialog').close());
  $('dialog-cancel').addEventListener('click', () => $('draft-dialog').close());
  $('draft-form').addEventListener('submit', saveDraft);
  $('draft-file').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { $('draft-error').textContent = 'Please choose a text file smaller than 2 MB.'; $('draft-error').hidden = false; return; }
    try {
      $('draft-text').value = await file.text();
      $('file-name').textContent = file.name;
      if (!$('draft-title').value.trim()) $('draft-title').value = file.name.replace(/\.(txt|md)$/i, '').replaceAll('_', ' ');
      $('draft-error').hidden = true;
    } catch (_) { $('draft-error').textContent = 'This file could not be read. Try pasting your text instead.'; $('draft-error').hidden = false; }
  });
  $('reset-button').addEventListener('click', () => $('reset-dialog').showModal());
  $('reset-close').addEventListener('click', () => $('reset-dialog').close());
  $('reset-cancel').addEventListener('click', () => $('reset-dialog').close());
  $('reset-confirm').addEventListener('click', resetDemo);
  $('settings-button').addEventListener('click', openSettings);
  $('setup-button').addEventListener('click', openSettings);
  $('settings-close').addEventListener('click', () => { if (!settingsBusy) $('settings-dialog').close(); });
  $('settings-dialog').addEventListener('cancel', (event) => { if (settingsBusy) event.preventDefault(); });
  $('settings-dialog').addEventListener('close', () => { $('settings-key').value = ''; providerDrafts = {}; });
  $('settings-form').addEventListener('submit', saveSettings);
  $('settings-test').addEventListener('click', testSettings);
  $('settings-provider').addEventListener('change', changeProvider);
  $('settings-base-url').addEventListener('input', () => { $('settings-key').value = ''; renderProviderFields(); settingsFeedback(''); });
  ['settings-model', 'settings-key'].forEach((id) => $(id).addEventListener('input', () => settingsFeedback('')));
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !busy) loadState(); });
  loadState();
  loadSettings({ prompt: true });
})();
