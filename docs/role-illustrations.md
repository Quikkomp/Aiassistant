# Role-card illustrations

Generated with the built-in `image_gen` tool (not the CLI). Each illustration was generated separately, inspected, and copied unchanged into the repository. Both PNGs are 1254 × 1254 RGBA with genuine transparent backgrounds. CSS scales them for display without altering the source files.

Assets:

- `local_chat_site/static/role-teacher-anime-v1.png`: glasses, pointer and chalkboard.
- `local_chat_site/static/role-student-anime-v1.png`: anatomical right hand raised; left forearm resting horizontally on a desk.

These decorative assets replace the paper decorations at the top right of the role cards. The role titles still provide the accessible labels. On smaller screens their display size decreases; hover motion respects reduced-motion preferences. No existing asset was overwritten.

## Final teacher prompt

```text
Use case: illustration-story. Asset type: production website role-card cutout illustration, a single teacher mascot, on a genuinely transparent background with alpha. Primary request: friendly anime/cartoon adult teacher wearing clearly visible round glasses, holding a slim teaching pointer and pointing its tip at a small chalkboard. The teacher is on the left of the small board, waist-up three-quarter pose with face visible and a gentle confident smile; the pointing arm, hand, pointer tip and entire board are fully inside the frame. Other arm relaxed near waist. Style: polished Japanese-anime-inspired 2D chibi editorial illustration, roughly three-head character proportions, rounded expressive features, clean thin dark-navy outlines, simple soft cel shading, not 3D and not photorealistic. Color palette to fit a quiet blue-white education website: cornflower/periwinkle blue teacher cardigan over white shirt, dark navy hair/eyes and glasses, warm natural skin tones; a pale sage chalkboard with a simple white chalk triangle and two small chalk lines, no readable text. Composition: compact near-square silhouette, transparent around both teacher and board, 5% outer padding, large clear face, uncluttered, legible at 150px display size, all hands anatomically coherent. Constraints: exactly one teacher and one small chalkboard, no extra people, no room or scene background, no colored rectangle or white backdrop, no enclosing badge or circle, no typography, no watermark or logo. This is a standalone asset, do not render any website UI or the supplied screenshot.
```

## Final student prompt

```text
Use case: illustration-story. Asset type: production website role-card cutout illustration, a single student mascot, on a genuinely transparent background with alpha. Primary request: friendly anime/cartoon student raising their RIGHT hand to answer a classroom question, while their LEFT forearm lies flat horizontally on a minimal desk edge in front. Front-facing waist-up pose: the student's anatomical RIGHT arm is on the viewer's LEFT, bent naturally with an open hand held above the head; the student's anatomical LEFT forearm is on the viewer's RIGHT, resting horizontally across the little desk. Both arms, all fingers, raised hand and desk edge must be fully visible, not cropped. Cheerful attentive expression looking forward. Style: polished Japanese-anime-inspired 2D chibi editorial illustration, roughly three-head character proportions, rounded expressive features, clean thin dark-navy outlines, simple soft cel shading, not 3D and not photorealistic. Match a paired teacher mascot in a quiet blue-white education website: white shirt with muted mint/sage school vest or collar, navy hair/eyes, warm natural skin tones, pale mint desktop accent. Composition: compact near-square silhouette centered, transparent around figure, 5% outer padding, large clear face, uncluttered, legible at 150px display size. Constraints: exactly one student and a minimal desk edge only, anatomically coherent two arms, no extra people, no classroom background, no colored rectangle or white backdrop, no enclosing badge or circle, no typography, no watermark or logo. This is a standalone asset, do not render any website UI or the supplied screenshot.
```
