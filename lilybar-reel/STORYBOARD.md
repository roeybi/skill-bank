# The Lily Bar: Signature Bouquets, 15 s showreel

1920x1080, 60 fps, 120 BPM (beat = 0.5 s, bar = 2 s), 30 beats.

## What the research found

thelilybar.co sits behind a Cloudflare bot check, so the page could not be opened or screenshotted
from this environment. Everything below comes from search-engine snapshots of the shop's own pages
(home, about-us, cart, products/latest, condolence-stands).

- **Who**: The Lily Bar Sdn Bhd, a florist in Petaling Jaya, Selangor, Malaysia. Fresh and artificial
  flowers, custom bridal bouquets, delivery services; "curated floral arrangements for all occasions".
- **Where**: delivery across the Klang Valley.
- **Same-day**: the cart page says the cut-off for same-day delivery is 5PM, and asks customers to
  WhatsApp the shop directly for same-day and next-day delivery.
- **Navigation (real labels)**: New Collection, Signature Bouquets, Fresh Bouquets, Soap Bouquets,
  Blue Series, Bridal Bouquet, Sympathy Flowers (also Congratulatory Blooms, Floral Box & Vase,
  Fruits & Vegetables, Graduation & Sunflower).
- **Products and prices (RM, from the shop's product listing)**:
  - Elora: RM 349 → RM 339 (-3%), 31 sold
  - Rubelle: RM 468 → RM 459 (-2%), 27 sold
  - Sylva: RM 268 → RM 259 (-3%)
  - Cinderella: RM 179 – RM 429
  - The snapshots do not say which products sit in the Signature Bouquets collection, so these four
    stand in for it. They live in one `PRODUCTS` array at the top of `scene.html`.
- **Not obtainable**: the real page layout, product photos, logo file, brand colours and typeface.

### What that means for the build

- The UI is a vector rebuild of the shop's real structure (header, category nav, collection grid,
  product card fields, cart with delivery note), not a pixel copy of its look.
- Product photos are replaced by one neutral line-drawing bouquet style (no invented flower colours).
- The logo is not redrawn. The end card typesets the name "The Lily Bar" in the chosen typeface.
- Colours and type are stand-ins: Fraunces (one family throughout), cream `#F3ECE3`, ink `#2B2320`,
  one accent, deep rose `#A8244B`, used only on the through-line object and the key word "today".

## Through-line object

**The pill**: the accent "Signature Bouquets" tab from the site's category nav.

It is born from the dot of the question mark in the hook, and from then on it keeps turning into the next UI element:
question-mark dot → nav tab → Elora's price tag → Add to Cart button → "WhatsApp us" button →
a field that fills the frame → a 5PM clock face → the tittle (dot) of the "i" in "The Lily Bar".

## Beat-by-beat storyboard

| Beat | Time | What happens | Sound |
|---|---|---|---|
| **Hook** | | | |
| 1 | 0.0 | "Need" rises out of a mask, huge type. Camera pushes from 1.00 | kick |
| 2 | 0.5 | "flowers" rises | kick |
| 3 | 1.0 | "today?" rises; "today" is the accent key word | kick |
| 4 | 1.5 | The "?" erases down to its dot; the dot stretches left into the pill and swallows "today"; "Signature Bouquets" rises inside it | kick, pop |
| **Moment 1: browse the collection** | | | |
| 5 | 2.0 | Camera pulls out: the pill is a tab in the real nav. The page opens from it as a circular mask; the other categories slide out from behind it; "Need flowers" drops away | kick, **hit**, whoosh |
| 6 | 2.5 | Cursor glides in to the tab | kick |
| 7 | 3.0 | Click: the pill squishes | kick, click |
| 8 | 3.5 | "Signature Bouquets" title rises; four product cards unfold top-down; camera eases out to the whole page | kick, ticks |
| **Moment 2: one bouquet, one price** | | | |
| 9 | 4.0 | The pill leaves the nav (an underline marks the active tab) and lands as Elora's price tag "RM 339"; camera zooms into the card | kick, **hit**, whoosh |
| 10 | 4.5 | "RM 349" rises and gets struck through | kick |
| 11 | 5.0 | "-3%" badge unfolds | kick |
| 12 | 5.5 | "31 sold" counts up from 0 | kick, ticks |
| **Moment 3: same-day, by 5PM** | | | |
| 13 | 6.0 | The price tag stretches into the "Add to Cart" button; cursor moves onto it | kick, **hit** |
| 14 | 6.5 | Click. The cart drawer wipes in from the right; camera whips across with directional blur; the pill flies along | kick, click, whoosh |
| 15 | 7.0 | The pill lands as the "WhatsApp us" button; "Your cart: Elora, RM 339" rises | kick |
| 16 | 7.5 | "Delivery: cut-off time for same-day delivery: 5PM" | kick |
| 17 | 8.0 | "For same-day and next-day delivery, WhatsApp us directly." Riser starts | kick |
| 18 | 8.5 | "Delivering across the Klang Valley"; cursor moves to the button | kick |
| 19 | 9.0 | Click on "WhatsApp us"; camera pushes into the pill | kick, click |
| 20 | 9.5 | The pill swells; cursor leaves | kick, swoosh-up |
| **Payoff** | | | |
| 21 | 10.0 | **Biggest beat.** The pill fills the frame past all four corners; "Order by" rises in cream | kick, **big hit**, drop |
| 22 | 10.5 | "5PM." rises | kick |
| 23 | 11.0 | The field contracts into a disc (a clock face, hands growing from the centre); "Delivered" rises | kick |
| 24 | 11.5 | "today." rises in the accent; the hour hand swings to 5 | kick |
| **End card** | | | |
| 25 | 12.0 | "Delivered today." drops away; the disc shrinks and flies; "The Lily Bar" rises letter by letter | kick, **hit** |
| 26 | 12.5 | The disc lands as the dot of the "i" in "Lily" | kick, pop |
| 27 | 13.0 | "Order by 5PM for same-day delivery" rises | kick |
| 28 | 13.5 | "thelilybar.co" rises | kick |
| 29-30 | 14.0-15.0 | End-card hold; camera keeps pushing | kicks ring out |

## Motion rules applied

- Springs everywhere (damping 0.82-0.95, tiny overshoot); eased tweens only for clip reveals.
- Nothing appears from nothing: text rises out of masks, the page opens from the pill, nav items slide
  out from behind it, cards and the drawer unfold through clip masks.
- The camera never stops: a continuous push of 4% per 2 s bar multiplies every Screen Studio-style zoom,
  so each scene starts at the zoom the last one ended on.
- Directional blur follows the pill's and the camera's screen speed on fast moves, on top of 3-subframe motion blur.
- Banned and absent: particles, glows, flares, shake, RGB split, crossfades, generic gradients, bouncy easing.
