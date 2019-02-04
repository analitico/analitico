/**
 * Base abstract class for a plugin.
 * Plugins are used to process datasets
 */
import { BehaviorSubject } from 'rxjs';

export abstract class AoPluginComponent  {
    // plugin data will be observed and modified using dataSubject
    dataSubject: BehaviorSubject<any>;
}
