import { BehaviorSubject } from 'rxjs';
export interface IAoPluginInstance {
    pluginsService: any;
    dataSubject: BehaviorSubject<any>;
}
