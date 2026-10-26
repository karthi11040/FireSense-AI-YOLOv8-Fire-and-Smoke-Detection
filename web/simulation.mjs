// A toy response model, not physical fire dynamics or a severity estimator.
export class Simulation {
  constructor() { this.auto = true; this.reset(); }
  reset() {
    this.history = []; this.confirmed = false; this.sprinkler = false;
    this.intensity = 0; this.fire = false; this.smoke = false;
  }
  observe(fire, smoke) {
    this.fire = fire; this.smoke = smoke;
    this.history.push(Boolean(fire));
    if (this.history.length > 5) this.history.shift();
    if (fire && !this.confirmed) this.intensity = Math.max(this.intensity, 30);
    if (!this.confirmed && this.history.filter(Boolean).length >= 3) {
      this.confirmed = true;
      this.intensity = Math.max(this.intensity, 60);
      this.sprinkler = this.auto;
      return true;
    }
    return false;
  }
  tick(dt) {
    if (!Number.isFinite(dt) || dt <= 0) return;
    dt = Math.min(dt, 1);
    const growth = this.fire ? 4 : 0;
    this.intensity = Math.max(0, Math.min(100, this.intensity + (growth - (this.sprinkler ? 16 : 0)) * dt));
  }
}
