import { TestBed } from '@angular/core/testing';

import { AoJobService } from './ao-job.service';

describe('AoJobService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: AoJobService = TestBed.get(AoJobService);
    expect(service).toBeTruthy();
  });
});
