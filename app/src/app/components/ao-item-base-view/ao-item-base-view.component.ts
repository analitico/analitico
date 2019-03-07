import { Component, OnInit, Input } from '@angular/core';
import { IAoItemView } from '../ao-item-view-interface';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';

@Component({
    selector: 'app-ao-item-base-view',
    templateUrl: './ao-item-base-view.component.html',
    styleUrls: ['./ao-item-base-view.component.css']
})
export class AoItemBaseViewComponent implements OnInit, IAoItemView {
    _item: any;
    _type: any;
    route: string;
    title: string;

    constructor(protected itemService: AoItemService) { }

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
    }

    ngOnInit() {
    }

    onLoad() {
        this.route = this.item.links.self.substring(this.item.links.self.indexOf('/api') + 4);
        this.title = (this.item.attributes && this.item.attributes.title) ? this.item.attributes.title : this.item.id;
    }

    changeItemTitle($event) {
        $event.target.blur();
        return this.itemService.saveItem(this.item);
    }

}