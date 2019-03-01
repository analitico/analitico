/**
 * Abstract component that will incapsulate all the item view types.
 * It will select the correct component view according to object type and required type of view
 * E.g., dataset preview view, dataset list view.
 */
import { Component, OnInit, ViewChild, AfterViewInit, ViewContainerRef, Input, ComponentFactoryResolver } from '@angular/core';
import { AoAnchorDirective } from 'src/app/directives/ao-anchor/ao-anchor.directive';
import { AoModelListViewComponent } from '../ao-model-list-view/ao-model-list-view.component';
import { IAoItemView } from '../ao-item-view-interface';
import { AoItemBaseViewComponent } from '../ao-item-base-view/ao-item-base-view.component';

@Component({
    selector: 'app-ao-item-view',
    templateUrl: './ao-item-view.component.html',
    styleUrls: ['./ao-item-view.component.css']
})
export class AoItemViewComponent implements OnInit, AfterViewInit {
    @ViewChild(AoAnchorDirective) aoAnchor: AoAnchorDirective;
    viewContainerRef: ViewContainerRef;
    _item: any;
    _type: string;

    get item(): any {
        return this._item;
    }
    @Input() set item(item: any) {
        this._item = item;
        this.onLoad();
    }

    get type(): string {
        return this._type;
    }
    @Input() set type(type: string) {
        this._type = type;
        this.checkIfCanBeLoaded();
    }

    constructor(protected componentFactoryResolver: ComponentFactoryResolver) { }

    ngOnInit() {
    }

    ngAfterViewInit() {
        // get the view of the anchor component
        this.viewContainerRef = this.aoAnchor.viewContainerRef;
        setTimeout(this.checkIfCanBeLoaded.bind(this));
    }

    // this is called when the item object is set
    onLoad() {
        this.checkIfCanBeLoaded();
    }
    // checkpoint: waits to have both item data and view ref
    checkIfCanBeLoaded() {
        if (this.item && this.item.type && this.viewContainerRef && this._type) {
            // clear view
            this.viewContainerRef.clear();
            // get the correct component
            let component = null;
            switch (this.item.type) {
                case 'analitico/model':
                    if (this._type === 'list') {
                        component = AoModelListViewComponent;
                    }
                    break;
            }
            if (!component) {
                component = AoItemBaseViewComponent;
            }
            if (component) {
                // get the component factory
                const componentFactory = this.componentFactoryResolver.resolveComponentFactory(component);
                // add the component to the anchor view
                const componentRef = this.viewContainerRef.createComponent(componentFactory);
                const instance = (<IAoItemView>componentRef.instance);
                // inject plugin service
                instance.item = this.item;
            }
        }
    }
}
