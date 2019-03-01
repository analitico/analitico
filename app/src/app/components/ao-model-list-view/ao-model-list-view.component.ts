/**
 * List view for a model
 */
import { Component, OnInit, Input } from '@angular/core';
import { IAoItemView } from '../ao-item-view-interface';
import { AoItemService } from 'src/app/services/ao-item/ao-item.service';
import { AoItemBaseViewComponent } from '../ao-item-base-view/ao-item-base-view.component';

@Component({
    selector: 'app-ao-model-list-view',
    templateUrl: './ao-model-list-view.component.html',
    styleUrls: ['./ao-model-list-view.component.css']
})
export class AoModelListViewComponent extends AoItemBaseViewComponent implements OnInit, IAoItemView {

    constructor(protected itemService: AoItemService) {
        super(itemService);
    }

    key1Name: string;
    key1Value: any;

    onLoad() {
        super.onLoad();
        // check algoritm type to select KPI
        this.checkAlghoritmType();
    }

    checkAlghoritmType() {
        // "algorithm": "ml/binary-classification"
        if (this.item.attributes.training && this.item.attributes.training.algorithm) {
            switch (this.item.attributes.training.algorithm) {
                case 'ml/binary-classification':
                default:
                    this.key1Name = 'Log loss';
                    this.key1Value = this.item.attributes.training.scores.log_loss;
                    break;
            }
        }
    }
}
