import { Component, OnInit, ViewChild } from '@angular/core';
import { JsonEditorComponent, JsonEditorOptions } from 'ang-jsoneditor';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';

@Component({
    templateUrl: './ao-raw-json-plugin.component.html',
    styleUrls: ['./ao-raw-json-plugin.component.css']
})
export class AoRawJsonPluginComponent extends AoPluginComponent implements OnInit {
    @ViewChild(JsonEditorComponent) editor: JsonEditorComponent;
    editorOptions: JsonEditorOptions;
    editorInterval: any;

    constructor() {
        super();
        // initialize JSON editor
        this.editorOptions = new JsonEditorOptions();
        this.editorOptions.modes = ['code']; // set all allowed modes
        this.editorOptions.mode = 'code';
        this.editorOptions.mainMenuBar = false;
    }

    ngOnInit() {
       // this.editorInterval = setInterval(this.resizeEditor.bind(this), 2000);
    }


    // called when, after a change, a valid JSON is present in the editor
    // if the JSON is not valid this is not called
    onEditorChange(data: any) {
        const that = this;
        // this is a special case because we need to completely replace the object
        // but in JS there is no *pointer
        // remove all keys
        Object.keys(this.data).forEach(function (key) { delete that.data[key]; });
        // copy all keys
        for (const key in data) {
            if (data.hasOwnProperty(key)) {
                this.data[key] = data[key];
            }
        }
        // notify change
        this.notifyChange();
    }


}
