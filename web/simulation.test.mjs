import test from 'node:test';
import assert from 'node:assert/strict';
import {Simulation} from './simulation.mjs';

test('three of five samples confirm one latched incident', () => {
  const s = new Simulation();
  for (const fire of [true, false, true, false]) assert.equal(s.observe(fire, false), false);
  assert.equal(s.observe(true, false), true);
  assert.equal(s.confirmed, true);
  assert.equal(s.sprinkler, true);
  assert.equal(s.observe(true, true), false);
  for (let i=0; i<5; i++) s.observe(false, false);
  assert.equal(s.confirmed, true);
});
test('smoke alone does not start virtual water', () => {
  const s = new Simulation();
  for (let i=0; i<8; i++) s.observe(false, true);
  assert.equal(s.confirmed, false);
  assert.equal(s.sprinkler, false);
});
test('water reduces toy intensity; reset clears the incident', () => {
  const s = new Simulation();
  for (let i=0; i<3; i++) s.observe(true, false);
  const before = s.intensity;
  s.tick(1);
  assert.ok(s.intensity < before);
  for (let i=0; i<30; i++) s.tick(1);
  assert.equal(s.intensity, 0);
  s.reset();
  assert.equal(s.confirmed, false);
  assert.equal(s.sprinkler, false);
});
test('manual mode waits for a water action', () => {
  const s = new Simulation(); s.auto = false;
  for (let i=0; i<3; i++) s.observe(true, false);
  assert.equal(s.sprinkler, false);
  const before = s.intensity; s.tick(1); assert.ok(s.intensity > before);
  s.sprinkler = true; s.tick(1); assert.ok(s.intensity < before+4);
});
test('simulation uses elapsed seconds independently of rendering cadence', () => {
  const coarse=new Simulation(), fine=new Simulation();
  for(const s of [coarse,fine]){s.auto=false;for(let i=0;i<3;i++)s.observe(true,false);}
  coarse.tick(5);
  for(let i=0;i<50;i++)fine.tick(.1);
  assert.ok(Math.abs(coarse.intensity-fine.intensity)<1e-8);
  assert.equal(coarse.elapsed,5);
  coarse.tick(NaN);coarse.tick(-1);assert.equal(coarse.elapsed,5);
});
