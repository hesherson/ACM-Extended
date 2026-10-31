// Geometry mirrors fn_updateTransfusionCards; values are native physical pixels,
// scaled together to the browser viewport rather than using independent font/icon vh guesses.
export function cardLayout(layout, card) {
  const [w,h,u,rowH,gap,radius]=layout || [360,227,1080,109.72,7.56,7];
  const pad=w*.045, iconW=u*.030, textX=pad+iconW+w*.025;
  const vialH=Math.min(u*.026,rowH*.30), vialW=vialH*.55;
  const trackW=w-textX-pad, nameH=Math.min(u*.021,rowH*.25), detailH=Math.min(u*.017,rowH*.22);
  const statusH=Math.min(u*.015,rowH*.20), thermalH=Math.min(u*.014,rowH*.19);
  const contentH=nameH+(card.detail?detailH:0)+(card.status?statusH:0)+(card.thermal?thermalH:0);
  const top=Math.max(((card.fraction>=0?rowH*.75:rowH*.91)-contentH)/2,0);
  const rect=(x,y,width,height)=>({left:`${100*x/w}%`,top:`${100*y/rowH}%`,width:`${100*width/w}%`,height:`${100*height/rowH}%`});
  const font=value=>`${100*u*value/h}vh`;
  return {root:{'--u':`${100*u/h}vh`,'--gap':`${100*gap/h}vh`,'--radius':`${100*radius/h}vh`},
    name:{...rect(textX,top,Math.max(w-textX-pad-(card.vial?vialW:0),0),nameH),fontSize:font(.018)},
    detail:{...rect(textX,top+nameH,Math.max(w-textX-pad-(card.vial?vialW:0),0),detailH),fontSize:font(.014)},
    status:{...rect(textX,top+nameH+(card.detail?detailH:0),trackW,statusH),fontSize:font(.0125)},
    thermal:{...rect(textX,top+nameH+(card.detail?detailH:0)+(card.status?statusH:0),trackW,thermalH),fontSize:font(.0125)},
    icon:rect(pad,top,iconW,contentH),vial:rect(w-pad-vialW,top,vialW,vialH),
    volume:{...rect(textX,rowH*.79,trackW,rowH*.21),fontSize:font(.010),'--track-height':`${100*u*.0025/h}vh`},
    mark:{top:`${100*u*.004/h}vh`,lineHeight:`${100*rowH*.15/h}vh`},
    tick:{top:`${-100*u*.006/h}vh`,height:`${100*u*.006/h}vh`}};
}
