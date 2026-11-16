// Native owns pane size, row gaps and font calibration. The inner card
// uses an 8 px grid at the 1080 px reference size, scaled with those metrics.
export function cardLayout(layout, card, fontScale = 1) {
  const [width, height, unit, rowHeight, gap, radius, rows = 2] =
    layout || [360, 227, 1080, 109.72, 7.56, 7];
  const compact = rows === 5;
  const step = Math.min(8 * unit / 1080, width / 20);
  const inset = 2 * step;
  const iconColumn = 7 * step;
  const textLeft = inset + iconColumn + step;
  const right = width - inset;
  const trackWidth = right - textLeft;
  const iconSize = Math.min(rowHeight * (compact ? .80 : .62), unit * .052, iconColumn + step);
  const vialHeight = Math.min(unit * .026, rowHeight * .30);
  const vialWidth = Math.min(vialHeight * .55, 2 * step);
  const captionRight = right - (card.vial ? vialWidth + step : 0);
  const captionWidth = captionRight - textLeft;

  const viewportHeight = value => (100 * value / height) + 'vh';
  const rect = (x, y, w, h) => ({
    left: (100 * x / width) + '%',
    top: (100 * y / rowHeight) + '%',
    width: (100 * w / width) + '%',
    height: (100 * h / rowHeight) + '%'
  });
  const caption = (x, y, w, h, size) => ({
    ...rect(x, y, w, h),
    fontSize: viewportHeight(unit * size * fontScale),
    lineHeight: viewportHeight(h)
  });

  const trackTop = rowHeight * (compact ? .72 : .79);
  const iconX = inset + (iconColumn - iconSize) / 2;
  const iconAreaHeight = compact ? rowHeight : trackTop;
  const geometry = {
    root: { '--rows': rows, '--gap': viewportHeight(gap), '--radius': viewportHeight(radius) },
    icon: rect(iconX, (iconAreaHeight - iconSize) / 2, iconSize, iconSize),
    volume: {
      ...rect(textLeft, trackTop, trackWidth, rowHeight - trackTop),
      fontSize: viewportHeight(unit * (compact ? .009 : .010) * fontScale),
      '--track-height': viewportHeight(unit * .0035)
    },
    flowStripe: { width: viewportHeight(trackWidth * 32 / 31) },
    mark: {
      top: viewportHeight(unit * (compact ? .0015 : .003)),
      lineHeight: viewportHeight(rowHeight * (compact ? .225 : .17))
    },
    tick: { top: viewportHeight(-unit * .002), height: viewportHeight(unit * .006) }
  };

  if (compact) {
    const firstLine = Math.min(unit * .017, trackTop * .53);
    const secondLine = Math.min(unit * .013, trackTop - firstLine);
    const top = (trackTop - firstLine - secondLine) / 2;
    const leadingWidth = Math.round(captionWidth * .5 / step) * step;
    const trailingLeft = textLeft + leadingWidth + step;
    const trailingWidth = Math.max(captionRight - trailingLeft, 0);
    return {
      ...geometry,
      name: caption(textLeft, top, card.status ? leadingWidth : captionWidth, firstLine, .014),
      detail: caption(textLeft, top + firstLine, card.thermal ? leadingWidth : captionWidth, secondLine, .011),
      status: { ...caption(trailingLeft, top, trailingWidth, firstLine, .010), textAlign: 'right' },
      thermal: { ...caption(trailingLeft, top + firstLine, trailingWidth, secondLine, .010), textAlign: 'right' },
      vial: rect(right - vialWidth, top, vialWidth, vialHeight)
    };
  }

  const nameHeight = Math.min(unit * .021, rowHeight * .22);
  const detailHeight = Math.min(unit * .017, rowHeight * .18);
  const statusHeight = Math.min(unit * .015, rowHeight * .16);
  const thermalHeight = Math.min(unit * .014, rowHeight * .15);
  const textHeight = nameHeight + detailHeight + statusHeight + thermalHeight;
  const top = Math.min(step, trackTop - textHeight);
  const detailTop = top + nameHeight;
  const statusTop = detailTop + detailHeight;
  const thermalTop = statusTop + statusHeight;
  return {
    ...geometry,
    name: caption(textLeft, top, captionWidth, nameHeight, .018),
    detail: caption(textLeft, detailTop, captionWidth, detailHeight, .014),
    status: caption(textLeft, statusTop, trackWidth, statusHeight, .0125),
    thermal: caption(textLeft, thermalTop, trackWidth, thermalHeight, .0125),
    vial: rect(right - vialWidth, top, vialWidth, vialHeight)
  };
}

// Match a stable engine-measured sample, never the live volume/name string.
export const FONT_PROBE = 'Hg0123456789';
export function nativeFontScale(probe, measuredWidth, viewportWidth, nativeWidth) {
  if (!probe || !Number.isFinite(measuredWidth) || measuredWidth <= 0) return null;
  const scale = probe[0] * viewportWidth / nativeWidth / measuredWidth;
  return Number.isFinite(scale) && scale >= .25 && scale <= 4 ? scale : null;
}

// Same smooth proximity curve as the native label painter. No prediction beyond the received volume.
export function markScale(fraction, mark, count) {
  if (fraction < 0 || count < 2) return 1;
  const near=Math.max(0,Math.min(1,1-Math.abs(fraction-mark)/(.7/(count-1))));
  return 1+.35*near*near*(3-2*near);
}
