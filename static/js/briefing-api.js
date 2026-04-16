/**
 * briefing-api.js — Adapter that replaces mock briefing content with live data.
 *
 * Injected into mock-briefing.html by BriefingPageHandler.
 * Fetches /api/briefing, replaces each section if data is available.
 * If stale or missing, shows a banner and polls until refresh completes.
 */
(function () {
  'use strict';

  var POLL_INTERVAL = 5000; // 5 seconds while refresh is running
  var pollTimer = null;

  // ── Utility ──────────────────────────────────────────────
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function priorityDot(p) {
    return '<span class="priority-dot p' + (p || 3) + '"></span>';
  }

  // ── Banner ───────────────────────────────────────────────
  function showBanner(msg, type) {
    var existing = document.getElementById('briefing-banner');
    if (existing) existing.remove();

    var banner = document.createElement('div');
    banner.id = 'briefing-banner';
    banner.style.cssText =
      'padding:10px 20px;font-size:13px;font-weight:500;display:flex;' +
      'align-items:center;gap:8px;border-bottom:1px solid var(--border);';

    if (type === 'refreshing') {
      banner.style.background = 'var(--ai-light)';
      banner.style.color = 'var(--ai)';
      banner.innerHTML = '<span class="spin">✦</span> ' + esc(msg);
    } else if (type === 'error') {
      banner.style.background = '#fce4ec';
      banner.style.color = '#c62828';
      banner.innerHTML = '⚠ ' + esc(msg);
    } else if (type === 'stale') {
      banner.style.background = '#fff3e0';
      banner.style.color = '#e65100';
      banner.innerHTML = '⏳ ' + esc(msg) +
        ' <button onclick="triggerBriefingRefresh()" style="margin-left:auto;padding:4px 12px;' +
        'border-radius:4px;border:1px solid currentColor;background:transparent;color:inherit;' +
        'cursor:pointer;font-family:inherit;font-size:12px;font-weight:600">Refresh now</button>';
    }

    var contentBody = document.querySelector('.content-body');
    if (contentBody) contentBody.parentNode.insertBefore(banner, contentBody);
  }

  function removeBanner() {
    var b = document.getElementById('briefing-banner');
    if (b) b.remove();
  }

  // ── CSS for spinner ──────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = '@keyframes briefing-spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}' +
    '.spin{display:inline-block;animation:briefing-spin 1.5s linear infinite}';
  document.head.appendChild(style);

  // ── Section renderers ────────────────────────────────────

  function renderAttention(data) {
    if (!data || !data.attention) return;
    var att = data.attention;

    // Stale follow-ups
    if (att.stale_followups && att.stale_followups.length > 0) {
      var card = document.querySelector('.insight-card.risk');
      if (card) {
        var items = att.stale_followups;
        var topPeople = items.slice(0, 3).map(function (i) { return '<strong>' + esc(i.person) + '</strong>'; });
        card.querySelector('.insight-title').innerHTML =
          items.length + ' people have been waiting on you for over a week';
        card.querySelector('.insight-body').innerHTML =
          'Your longest-open waiting items are with ' + topPeople.join(', ') +
          '. A quick "still on my radar" message prevents relationship damage.';

        var tasksEl = card.querySelector('.insight-tasks');
        if (tasksEl) {
          tasksEl.innerHTML = items.slice(0, 5).map(function (i) {
            return '<div class="insight-task">' + priorityDot(i.priority) +
              '<span class="it-id">#' + i.task_id + '</span>' +
              '<span class="it-title">' + esc(i.title) + '</span>' +
              '<span class="it-meta">' + i.days_waiting + 'd waiting</span></div>';
          }).join('');
        }
      }
    }
  }

  function renderInitiatives(data) {
    if (!data || !data.initiatives || !data.initiatives.length) return;

    var grid = document.querySelector('.initiative-grid');
    if (!grid) return;

    grid.innerHTML = data.initiatives.map(function (init) {
      var healthClass = (init.health || 'on-track').replace(/[\s_]/g, '-').toLowerCase();
      var healthLabel = init.health || 'On Track';
      // Capitalize first letter of each word
      healthLabel = healthLabel.replace(/\b\w/g, function (c) { return c.toUpperCase(); });

      var meta = '<span class="meta-item">📋 ' + (init.task_count || 0) + ' tasks</span>' +
        '<span class="meta-item">⏳ ' + (init.waiting_count || 0) + ' waiting</span>' +
        '<span class="meta-item">👥 ' + (init.people ? init.people.length : 0) + ' people</span>';

      var actions = '';
      if (init.actions && init.actions.length) {
        actions = '<div class="init-actions">' + init.actions.map(function (a) {
          var cls = a.type === 'ai' ? 'ai' : a.type === 'primary' ? 'primary' : 'secondary';
          var prefix = a.type === 'ai' ? '✦ ' : '';
          return '<button class="init-btn ' + cls + '">' + prefix + esc(a.label) + '</button>';
        }).join('') + '</div>';
      }

      return '<div class="init-col">' +
        '<div class="init-col-header">' +
        '<div class="init-col-name">' + esc(init.name) + '</div>' +
        '<span class="init-health ' + healthClass + '">' + esc(healthLabel) + '</span>' +
        '<div class="init-col-meta">' + meta + '</div>' +
        '</div>' +
        '<div class="init-cos">' +
        '<div class="init-cos-label">✦ Status Update</div>' +
        '<div class="init-cos-text" style="font-style:normal">' + (init.cos_narrative || '') + '</div>' +
        actions +
        '</div></div>';
    }).join('');
  }

  function renderCalendar(data) {
    if (!data || !data.calendar) return;
    var cal = data.calendar;

    // Today's calendar card
    var prepCard = document.querySelector('.insight-card.prep');
    if (prepCard && cal.today_summary) {
      prepCard.querySelector('.insight-title').innerHTML = esc(cal.today_summary);

      if (cal.today_meetings && cal.today_meetings.length) {
        var body = cal.today_meetings.map(function (m) {
          var related = m.related_task_ids && m.related_task_ids.length
            ? ' — related: ' + m.related_task_ids.map(function (id) { return '#' + id; }).join(', ')
            : '';
          return '<strong>' + esc(m.time) + '</strong> ' + esc(m.title) +
            (m.has_agenda === false ? ' <em>(no agenda)</em>' : '') + related;
        }).join('<br>');
        prepCard.querySelector('.insight-body').innerHTML = body;
      }

      var tasksEl = prepCard.querySelector('.insight-tasks');
      if (tasksEl) tasksEl.innerHTML = '';
    }

    // Week load
    var weekCard = document.querySelector('.insight-card.info');
    if (weekCard && cal.week_load && cal.week_load.length) {
      var maxHours = Math.max.apply(null, cal.week_load.map(function (d) { return d.hours || 0; }));
      if (maxHours < 1) maxHours = 8;

      var barsHtml = cal.week_load.map(function (d) {
        var pct = Math.round(((d.hours || 0) / 8) * 100);
        var level = d.hours >= 5 ? 'heavy' : d.hours >= 3 ? 'medium' : 'light';
        var todayClass = d.is_today ? ' today' : '';
        return '<div class="day-load-bar' + todayClass + '">' +
          '<div class="bar-label">' + esc(d.day) + '</div>' +
          '<div class="bar-fill-container"><div class="bar-fill ' + level + '" style="width:' + pct + '%"></div></div>' +
          '<div class="bar-hours">' + d.hours + 'h</div></div>';
      }).join('');

      var loadEl = weekCard.querySelector('.day-load');
      if (loadEl) loadEl.innerHTML = barsHtml;

      if (cal.recommendation) {
        var recEl = weekCard.querySelector('.rec-text');
        if (recEl) recEl.innerHTML = '<strong>Recommendation:</strong> ' + esc(cal.recommendation);
      }
    }
  }

  function renderPeople(data) {
    if (!data || !data.people || !data.people.length) return;

    var strip = document.querySelector('.people-strip');
    if (!strip) return;

    strip.innerHTML = data.people.map(function (p) {
      var badge = '';
      if (p.badge) {
        var badgeType = p.badge_type || 'risk';
        badge = '<span class="chip-badge ' + badgeType + '">' + esc(p.badge) + '</span>';
      }
      return '<div class="person-chip">' +
        '<div class="person-avatar" style="background:' + (p.color || '#616161') + '">' +
        esc(p.initials || '') + '</div>' +
        '<div><div class="person-chip-name">' + esc(p.name) + '</div>' +
        '<div class="person-chip-detail">' + esc(p.detail || '') + '</div></div>' +
        badge + '</div>';
    }).join('');

    // Relationship insight
    if (data.relationship_insight) {
      var ri = data.relationship_insight;
      var insightCard = document.querySelector('.insight-card.opportunity');
      if (insightCard) {
        insightCard.querySelector('.insight-title').innerHTML = esc(ri.title);
        insightCard.querySelector('.insight-body').innerHTML = esc(ri.body);

        if (ri.actions && ri.actions.length) {
          var actionsEl = insightCard.querySelector('.insight-actions');
          if (actionsEl) {
            actionsEl.innerHTML = ri.actions.map(function (a) {
              var cls = a.type === 'ai' ? 'ai' : a.type === 'primary' ? 'primary' : 'secondary';
              var prefix = a.type === 'ai' ? '✦ ' : '';
              return '<button class="insight-btn ' + cls + '">' + prefix + esc(a.label) + '</button>';
            }).join('');
          }
        }
      }
    }
  }

  function renderAll(data) {
    renderAttention(data);
    renderInitiatives(data);
    renderCalendar(data);
    renderPeople(data);

    // Re-linkify task IDs after content replacement
    linkifyTaskIds();
  }

  function linkifyTaskIds() {
    document.querySelectorAll('.it-id').forEach(function (el) {
      var m = el.textContent.match(/#(\d+)/);
      if (m && !el.querySelector('.task-link')) {
        el.innerHTML = '<a href="#" class="task-link" data-task-id="' + m[1] +
          '" onclick="openTaskPanel(' + m[1] + ');return false">' + el.textContent + '</a>';
      }
    });
    var containers = document.querySelectorAll(
      '.insight-body, .insight-title, .init-cos-text, .rec-text, .init-actions'
    );
    containers.forEach(function (el) {
      el.innerHTML = el.innerHTML.replace(/#(\d{2,4})(?![^<]*>)/g, function (match, id) {
        return '<a href="#" class="task-link" data-task-id="' + id +
          '" onclick="openTaskPanel(' + id + ');return false">' + match + '</a>';
      });
    });
  }

  // ── Refresh trigger ──────────────────────────────────────
  window.triggerBriefingRefresh = function () {
    showBanner('Generating fresh briefing...', 'refreshing');
    fetch('/api/briefing/refresh', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) startPolling();
        else showBanner('Refresh failed: ' + (d.message || 'unknown error'), 'error');
      })
      .catch(function () {
        showBanner('Could not start refresh', 'error');
      });
  };

  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(function () {
      fetch('/api/briefing')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.status === 'ready' && d.content) {
            stopPolling();
            removeBanner();
            renderAll(d.content);
            updateTimestamp(d.generated_at);
          } else if (d.status === 'error') {
            stopPolling();
            showBanner('Refresh failed: ' + (d.error_message || 'unknown'), 'error');
          }
          // else still running — keep polling
        });
    }, POLL_INTERVAL);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function updateTimestamp(generated_at) {
    if (!generated_at) return;
    var dateEl = document.getElementById('briefing-date');
    if (dateEl) {
      var gen = new Date(generated_at);
      var now = new Date();
      var sameDay = gen.toDateString() === now.toDateString();
      var timeStr = gen.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      dateEl.textContent = now.toLocaleDateString('en-US', {
        weekday: 'long', month: 'long', day: 'numeric'
      }) + (sameDay ? ' · Updated ' + timeStr : ' · Last updated ' + gen.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric'
      }) + ' ' + timeStr);
    }
  }

  // ── Init ─────────────────────────────────────────────────
  function init() {
    fetch('/api/briefing')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'ready' && d.content) {
          renderAll(d.content);
          updateTimestamp(d.generated_at);
          if (d.is_stale) {
            showBanner(
              'This briefing is from ' + new Date(d.generated_at).toLocaleDateString('en-US', {
                weekday: 'short', month: 'short', day: 'numeric'
              }) + '. Refresh for latest data.',
              'stale'
            );
          }
        } else if (d.status === 'running') {
          showBanner('Generating briefing...', 'refreshing');
          startPolling();
        } else if (d.status === 'empty' || !d.content) {
          // No briefing yet — keep mock content, show option to generate
          showBanner('No briefing generated yet. Click to generate your first briefing.', 'stale');
        } else if (d.status === 'error') {
          showBanner('Last refresh failed: ' + (d.error_message || 'unknown'), 'error');
        }
      })
      .catch(function () {
        // API not available — keep mock content silently
      });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
