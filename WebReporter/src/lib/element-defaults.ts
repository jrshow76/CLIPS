import type {
  TextElement, RectElement, LineElement, ImageElement, EllipseElement,
} from './types';

let counter = 1;
const nextId = () => `el-${Date.now()}-${counter++}`;
const nextZ  = () => counter;

export function createTextElement(x = 20, y = 20): TextElement {
  return {
    id: nextId(), type: 'text', name: '텍스트',
    x, y, width: 60, height: 10, locked: false, zIndex: nextZ(),
    content: '텍스트를 입력하세요',
    fontSize: 12, fontFamily: 'sans-serif',
    fontWeight: 'normal', fontStyle: 'normal', textDecoration: 'none',
    textAlign: 'left', color: '#222222', backgroundColor: 'transparent',
    borderColor: 'transparent', borderWidth: 0,
    paddingTop: 1, paddingBottom: 1, paddingLeft: 2, paddingRight: 2,
    lineHeight: 1.4,
  };
}

export function createRectElement(x = 20, y = 20): RectElement {
  return {
    id: nextId(), type: 'rect', name: '사각형',
    x, y, width: 50, height: 30, locked: false, zIndex: nextZ(),
    fillColor: '#ffffff', strokeColor: '#333333', strokeWidth: 1,
    borderRadius: 0, opacity: 1,
  };
}

export function createLineElement(x = 20, y = 20): LineElement {
  return {
    id: nextId(), type: 'line', name: '라인',
    x, y, width: 60, height: 1, locked: false, zIndex: nextZ(),
    color: '#333333', strokeWidth: 1, direction: 'horizontal', dashed: false,
  };
}

export function createImageElement(x = 20, y = 20): ImageElement {
  return {
    id: nextId(), type: 'image', name: '이미지',
    x, y, width: 50, height: 40, locked: false, zIndex: nextZ(),
    src: '', objectFit: 'contain', opacity: 1,
  };
}

export function createEllipseElement(x = 20, y = 20): EllipseElement {
  return {
    id: nextId(), type: 'ellipse', name: '타원',
    x, y, width: 40, height: 30, locked: false, zIndex: nextZ(),
    fillColor: '#ffffff', strokeColor: '#333333', strokeWidth: 1, opacity: 1,
  };
}
