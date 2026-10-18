import { test, expect } from '@playwright/test';

async function mock(page:any, silentUrgent=false) {
  let deliver=false;
  const first={supplier_id:'S001',p_link:.95,p_risk:.95,p_urgent:.95,is_risk:'Y',urgent:'Y',priority:70,priority_band:'high',needs_review:false,review_reasons:[],evidence_ids:['e1'],impact_status:'active',priority_requires_review:true,localized_warnings:['severity_confidence_low']};
  const second={...first,supplier_id:'S002',needs_review:true,review_reasons:['association_support_insufficient'],priority_requires_review:false};
  const article={id:'MOCK-REVIEW',headline:'MOCK · interrupción confirmada y otra exposición incierta',summary:'MOCK: dos evaluaciones independientes para probar política y UX.',source:'MOCK · sintético identificado',state:'review',version:1,published_date:'2026-10-18',analysis:{analysis_status:'review',is_risk:'Y',urgent:'Y',question_version:'link-3.0.0-dev',review_policy_version:'review-1.1.0-candidate',model_id:'MOCK',affected_supplier_ids:['S001','S002'],assessments:[first,second],evidence:[{id:'e1',text:'MOCK · hecho operativo'}],review_reasons:['association_support_insufficient:S002'],context_notes:[]}};
  await page.addInitScript(()=>{(window as any).__tones=0;const original=AudioContext.prototype.createOscillator;AudioContext.prototype.createOscillator=function(){(window as any).__tones++;return original.call(this)}});
  await page.route('**/api/**',async(route:any)=>{
    expect(route.request().method()).toBe('GET');
    const p=new URL(route.request().url()).pathname.slice(4);
    const baseAlert={revision:1,acknowledged:false,state:'active',priority:70,headline:'MOCK · alerta de política',created_at:'2026-10-18T12:00:00Z'};
    const alerts=deliver?[{...baseAlert,id:101,incident_id:'MOCK-I1',supplier_id:'S001',supplier_name:'MOCK sustentado',urgent:'Y',sound_eligible:!silentUrgent,needs_review:false},{...baseAlert,id:102,incident_id:'MOCK-I2',supplier_id:'S002',supplier_name:'MOCK incierto',urgent:'Y',sound_eligible:false,needs_review:true}]:[];
    const data:Record<string,any>={'/config':{bands:[],cooldown_seconds:30},'/session':{presenter:true,csrf:'MOCK'},'/overview':{},'/suppliers':{items:[]},'/articles':[article],'/articles/MOCK-REVIEW':article,'/articles/MOCK-REVIEW/runs':[],'/sources':[],'/batches':[],'/alerts':{items:alerts,unread:alerts.length,cursor:deliver?102:0}};
    await route.fulfill({json:data[p]??{}});
  });
  return ()=>{deliver=true};
}

for(const width of [360,390,768,1440])test(`Certeza y atención urgente separadas ${width}px · MOCK`,async({page})=>{
  await page.setViewportSize({width,height:960});const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await mock(page);await page.goto('/noticias/MOCK-REVIEW');
  const stable=page.getByLabel('Decisión y acción · S001',{exact:true}),uncertain=page.getByLabel('Decisión y acción · S002',{exact:true});
  await expect(stable.getByText('Análisis automático',{exact:true})).toBeVisible();
  await expect(stable.getByText('Acción inmediata:',{exact:false})).toBeVisible();
  await expect(stable.getByText('Prioridad estimada:',{exact:false})).toBeVisible();
  await expect(uncertain.getByText('Decisión por confirmar',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);expect(errors).toEqual([]);
  await stable.scrollIntoViewIfNeeded();await page.screenshot({path:`../reports/review-policy-mock-${width}.png`});
});

test('Urgencia automática no depende del umbral de audio · MOCK',async({page})=>{
  const deliver=await mock(page,true);deliver();await page.goto('/alertas');
  await expect(page.getByText('Acción inmediata',{exact:true})).toBeVisible();
  await expect(page.getByText('Requiere revisión',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>(window as any).__tones)).toBe(0);
});

test('Aviso automático por proveedor aunque otro requiera revisión · MOCK',async({page})=>{
  const deliver=await mock(page);await page.goto('/noticias/MOCK-REVIEW');
  await page.getByRole('button',{name:'Activar sonido',exact:true}).last().click();
  await expect(page.getByText('Activado',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>(window as any).__tones)).toBe(0);
  deliver();await expect.poll(()=>page.evaluate(()=>(window as any).__tones),{timeout:12000}).toBe(1);
  await page.waitForTimeout(3500);expect(await page.evaluate(()=>(window as any).__tones)).toBe(1);
  await expect(page).toHaveTitle(/\(2\)/);
});
