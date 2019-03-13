import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

@Component({
    selector: 'app-ao-smart-input-box',
    templateUrl: './ao-smart-input-box.component.html',
    styleUrls: ['./ao-smart-input-box.component.css']
})
export class AoSmartInputBoxComponent implements OnInit {

    constructor() { }

    @Input() item: any;
    @Input() placeholder: string;
    @Input() isEditing = false;
    @Output() newValue = new EventEmitter();
    editingValue: string;

    ngOnInit() {
        this.editingValue = '' + this.item;
    }

    edit() {
        this.isEditing = true;
    }

    abort() {
        this.editingValue = '' + this.item;
        this.isEditing = false;
    }

    changeValue() {
        this.isEditing = false;
        this.item = this.editingValue;
        // emit new value
        this.newValue.emit(this.editingValue);
    }

    onKeydown(event) {
        if (event.key === 'Enter') {
            if (this.item === this.editingValue) {
                return this.abort();
            }
            this.changeValue();
        } else if (event.key === 'Escape') {
            return this.abort();
        }
    }
}
