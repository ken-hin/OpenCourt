// conference_filter.js — Conference filtering with grow/shrink + FLIP slide animation.
//
// Two animation systems work together:
//
//  1. Grow/shrink (opacity + scale) on cards being shown or hidden.
//     Uses a .card-out CSS class that transitions transform and opacity.
//
//  2. FLIP - slide on cards that stay visible but move to fill empty space.
//     FLIP = First, Last, Invert, Play:
//       First — snapshot every visible card's position before anything changes
//       Last — hide the filtered-out cards so the browser reflows the layout
//       Invert — apply a translate() transform so each card looks like it's
//                still in its old position
//       Play — remove the transform; the CSS transition slides it to where
//                it actually is now
//
// DURATION must match the CSS transition duration in teams.html's <style> block.

const DURATION = 300; // ms

const filterBtns = document.querySelectorAll('.filter-btn[data-target]');
const teamCards  = document.querySelectorAll('.team-card');

/**
 * Shrink a card out, then remove it from the layout.
 * onComplete: fires after the card is fully hidden — used to trigger FLIP
 * once all hiding animations have finished.
 */
function hideCard(card, onComplete) {
  card.classList.add('card-out');
  setTimeout(() => {
    card.hidden = true;
    card.classList.remove('card-out'); // reset for next showCard()
    if (onComplete) onComplete();
  }, DURATION);
}

/**
 * Reveal a card and grow it in from the scaled-down state.
 * The card must be hidden (display:none) before this is called.
 */
function showCard(card) {
  card.classList.add('card-out');  // start in the scaled-down state (instant — card is hidden)
  card.hidden = false;             // put it back in the layout
  card.getBoundingClientRect();    // force reflow so the browser registers the start state
  card.classList.remove('card-out'); // triggers the grow-in transition
}

/**
 * FLIP: slide every remaining visible card from its old position to its new one.
 * prePositions — a Map of card → DOMRect captured before the layout changed.
 */
function flipCards(prePositions) {
  teamCards.forEach(card => {
    // Only animate cards that are still visible and were visible before
    if ( card.hidden || !prePositions.has(card) ) return;

    const first = prePositions.get(card);  // where it was
    const last  = card.getBoundingClientRect(); // where it is now

    const dx = first.left - last.left;
    const dy = first.top  - last.top;

    if ( dx === 0 && dy === 0 ) return; // card didn't move, skip

    // INVERT — snap card back to its old position instantly (no transition yet)
    card.style.transition = 'none';
    card.style.transform  = `translate(${dx}px, ${dy}px)`;

    // PLAY — next frame: re-enable transition and clear the transform so it
    // slides smoothly from the old position to the new (natural) one
    requestAnimationFrame(() => {
      card.style.transition = `transform ${DURATION}ms ease-in-out, opacity ${DURATION}ms ease-in-out`;
      card.style.transform  = '';

      // Once the slide finishes, remove the inline styles so the CSS
      // class rules (used by showCard/hideCard) take back over cleanly
      card.addEventListener('transitionend', () => {
        card.style.transition = '';
      }, { once: true });
    });
  });
}

/**
 * Read the checked filter buttons and animate cards in/out to match.
 * When nothing is checked, all cards are shown (default "show all" state).
 */
function applyFilter() {
  const activeTargets = Array.from(filterBtns).filter(btn => btn.checked).map(btn => btn.dataset.target);

  // Sort cards into buckets — only act on cards that actually need to change
  const toHide = [];
  const toShow = [];

  teamCards.forEach(card => {
    const shouldHide = activeTargets.length > 0 && !activeTargets.includes(card.id);
    if (shouldHide && !card.hidden) toHide.push(card);
    else if (!shouldHide && card.hidden) toShow.push(card);
  });

  if (toHide.length === 0 && toShow.length === 0) return;

  // FIRST — snapshot positions of all currently visible cards before anything moves
  const prePositions = new Map();
  teamCards.forEach(card => {
    if (!card.hidden) prePositions.set(card, card.getBoundingClientRect());
  });

  // Start hide animations. Once every card has finished shrinking and been
  // removed from layout (card.hidden = true), the browser reflows and FLIP
  // slides the remaining cards from their old positions to their new ones.
  let hiddenCount = 0;
  toHide.forEach(card => {
    hideCard(card, () => {
      hiddenCount++;
      if (hiddenCount === toHide.length) {
        // LAST + INVERT + PLAY — all hidden, now animate remaining cards
        flipCards(prePositions);
      }
    });
  });

  // Show cards with the grow-in animation simultaneously
  toShow.forEach(card => showCard(card));
}

// Re-run the filter whenever any checkbox changes state.
filterBtns.forEach(btn => btn.addEventListener('change', applyFilter));

// Wait one frame after reset so the browser clears checkbox values first,
// then applyFilter sees 0 checked boxes and shows everything.
document.querySelector('.conf-filter').addEventListener('reset', () => {
  requestAnimationFrame(applyFilter);
});
