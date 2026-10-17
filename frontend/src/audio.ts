// One controller per tab. Preferences never imply browser audio permission.
export class RadarAudio {
 context:AudioContext|null=null; enabled=false; muted=false; last=0;
 seen=new Set<string>(JSON.parse(sessionStorage.getItem('radar-sounded')||'[]'));
 async activate(){this.context??=new AudioContext();await this.context.resume();if(this.context.state!=='running')throw new Error('Audio bloqueado por el navegador');this.enabled=true;this.muted=false}
 mute(){this.muted=true;this.enabled=false}
 async play(){if(!this.context || this.context.state!=='running')throw new Error('Activa primero el sonido');
 const oscillator=this.context.createOscillator(),gain=this.context.createGain(),t=this.context.currentTime;
 oscillator.type='sine';oscillator.frequency.setValueAtTime(660,t);oscillator.frequency.setValueAtTime(880,t+.25);oscillator.frequency.setValueAtTime(660,t+.5);
 gain.gain.setValueAtTime(0,t);gain.gain.linearRampToValueAtTime(.13,t+.04);gain.gain.setValueAtTime(.13,t+.7);gain.gain.linearRampToValueAtTime(0,t+.95);
 oscillator.connect(gain);gain.connect(this.context.destination);oscillator.start(t);oscillator.stop(t+1);
 }
 async notify(alerts:{id:number;revision:number;sound_eligible:boolean;acknowledged:boolean}[],cooldown:number){
 const fresh=alerts.filter(a=>!this.seen.has(`${a.id}:${a.revision}`));
 for(const a of fresh)this.seen.add(`${a.id}:${a.revision}`);
 sessionStorage.setItem('radar-sounded',JSON.stringify([...this.seen]));
 if(this.enabled&&!this.muted&&Date.now()-this.last>=cooldown*1000&&fresh.some(a=>a.sound_eligible&&!a.acknowledged)){await this.play();this.last=Date.now()}
 }
}
export const audio=new RadarAudio();
