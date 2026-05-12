'use client';

import React from 'react';
import {
  Document, Page, View, Text, Image, Line, Svg,
  StyleSheet,
} from '@react-pdf/renderer';
import type { ReportTemplate, ReportElement } from './types';
import { getPageDimensions, mmToPt } from './paper-sizes';

// ─── PDF 요소 렌더러 ─────────────────────────────────────────────────────────

function PdfElement({ el }: { el: ReportElement }) {
  const pt = (mm: number) => mmToPt(mm);

  if (el.type === 'text') {
    return (
      <View
        style={{
          position: 'absolute',
          left:    pt(el.x),
          top:     pt(el.y),
          width:   pt(el.width),
          height:  pt(el.height),
          overflow: 'hidden',
          padding: `${pt(el.paddingTop)}pt ${pt(el.paddingRight)}pt ${pt(el.paddingBottom)}pt ${pt(el.paddingLeft)}pt`,
          backgroundColor: el.backgroundColor === 'transparent' ? undefined : el.backgroundColor,
          borderWidth:  el.borderWidth > 0 ? el.borderWidth : undefined,
          borderColor:  el.borderColor   !== 'transparent' ? el.borderColor : undefined,
          borderStyle: 'solid',
        }}
      >
        <Text
          style={{
            fontSize:   el.fontSize,
            fontWeight: el.fontWeight,
            color:      el.color,
            textAlign:  el.textAlign === 'justify' ? 'justify' : el.textAlign,
            lineHeight: el.lineHeight,
          }}
        >
          {el.content}
        </Text>
      </View>
    );
  }

  if (el.type === 'rect') {
    return (
      <View
        style={{
          position:        'absolute',
          left:            pt(el.x),
          top:             pt(el.y),
          width:           pt(el.width),
          height:          pt(el.height),
          backgroundColor: el.fillColor,
          borderWidth:     el.strokeWidth,
          borderColor:     el.strokeColor,
          borderStyle:     'solid',
          borderRadius:    el.borderRadius,
          opacity:         el.opacity,
        }}
      />
    );
  }

  if (el.type === 'ellipse') {
    return (
      <View
        style={{
          position:        'absolute',
          left:            pt(el.x),
          top:             pt(el.y),
          width:           pt(el.width),
          height:          pt(el.height),
          backgroundColor: el.fillColor,
          borderWidth:     el.strokeWidth,
          borderColor:     el.strokeColor,
          borderStyle:     'solid',
          borderRadius:    Math.min(pt(el.width), pt(el.height)) / 2,
          opacity:         el.opacity,
        }}
      />
    );
  }

  if (el.type === 'line') {
    const x1 = pt(el.x);
    const y1 = pt(el.y);
    const x2 = x1 + pt(el.width);
    const y2 = y1 + pt(el.height);

    let svgX1 = 0, svgY1 = 0, svgX2 = pt(el.width), svgY2 = 0;
    if (el.direction === 'vertical')       { svgX1 = pt(el.width)/2; svgY2 = pt(el.height); svgX2 = pt(el.width)/2; }
    if (el.direction === 'diagonal-down')  { svgX2 = pt(el.width); svgY2 = pt(el.height); }
    if (el.direction === 'diagonal-up')    { svgY1 = pt(el.height); svgX2 = pt(el.width); svgY2 = 0; }

    return (
      <Svg
        style={{
          position: 'absolute',
          left:   pt(el.x),
          top:    pt(el.y),
          width:  pt(el.width)  || 1,
          height: pt(el.height) || el.strokeWidth + 2,
        }}
      >
        <Line
          x1={svgX1} y1={svgY1} x2={svgX2} y2={svgY2}
          stroke={el.color}
          strokeWidth={el.strokeWidth}
          strokeDasharray={el.dashed ? `${el.strokeWidth * 4} ${el.strokeWidth * 2}` : undefined}
        />
      </Svg>
    );
  }

  if (el.type === 'image' && el.src) {
    return (
      <Image
        src={el.src}
        style={{
          position: 'absolute',
          left:     pt(el.x),
          top:      pt(el.y),
          width:    pt(el.width),
          height:   pt(el.height),
          opacity:  el.opacity,
          objectFit: el.objectFit === 'none' ? 'contain' : el.objectFit,
        }}
      />
    );
  }

  return null;
}

// ─── PDF 문서 ────────────────────────────────────────────────────────────────

interface ReportPdfDocumentProps {
  template: ReportTemplate;
}

export function ReportPdfDocument({ template }: ReportPdfDocumentProps) {
  const { pageSettings, elements } = template;
  const { width, height } = getPageDimensions(pageSettings.size, pageSettings.orientation);
  const pt = (mm: number) => mmToPt(mm);

  const sortedElements = [...elements].sort((a, b) => a.zIndex - b.zIndex);

  const styles = StyleSheet.create({
    page: {
      width:  pt(width),
      height: pt(height),
      position: 'relative',
      backgroundColor: '#ffffff',
      paddingTop:    pt(pageSettings.margins.top),
      paddingBottom: pt(pageSettings.margins.bottom),
      paddingLeft:   pt(pageSettings.margins.left),
      paddingRight:  pt(pageSettings.margins.right),
    },
    canvas: {
      position: 'absolute',
      top: 0, left: 0,
      width:  pt(width),
      height: pt(height),
    },
  });

  return (
    <Document title={template.name}>
      <Page size={[pt(width), pt(height)]} style={styles.page}>
        <View style={styles.canvas}>
          {sortedElements.map((el) => (
            <PdfElement key={el.id} el={el} />
          ))}
        </View>
      </Page>
    </Document>
  );
}
