import { TestBed } from '@angular/core/testing';

import { AoPluginsService } from './ao-plugins.service';

describe('AoPluginsService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: AoPluginsService = TestBed.get(AoPluginsService);
    expect(service).toBeTruthy();
  });
});
