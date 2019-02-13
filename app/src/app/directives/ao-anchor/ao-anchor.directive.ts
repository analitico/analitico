/**
 * Used to get a child view in parent component
 */
import { Directive, ViewContainerRef } from '@angular/core';

@Directive({
    selector: '[app-ao-anchor]',
})
export class AoAnchorDirective {
    constructor(public viewContainerRef: ViewContainerRef) { }
}
