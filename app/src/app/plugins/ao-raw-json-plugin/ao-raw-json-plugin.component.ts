import { Component, OnInit, ViewChild } from '@angular/core';
import { JsonEditorComponent, JsonEditorOptions } from 'ang-jsoneditor';
import { AoPluginComponent } from 'src/app/plugins/ao-plugin-component';

@Component({
    selector: 'app-ao-raw-json-plugin',
    templateUrl: './ao-raw-json-plugin.component.html',
    styleUrls: ['./ao-raw-json-plugin.component.css']
})
export class AoRawJsonPluginComponent extends AoPluginComponent implements OnInit {
    @ViewChild(JsonEditorComponent) editor: JsonEditorComponent;
    editorOptions: JsonEditorOptions;
    // the editor component will use a copy of the data
    editorData: any;
    constructor() {
        super();
        // initialize JSON editor
        this.editorOptions = new JsonEditorOptions();
        this.editorOptions.modes = ['code']; // set all allowed modes
        this.editorOptions.mode = 'code';
    }

    ngOnInit() {
    }

    setData(data: any) {
        super.setData(data);
        if (!this.editorData) {
            this.editorData = this.data;
        }
    }

    /** called when, after a change, a valid JSON is present in the editor
     *  if the JSON is not valid this is not called
    */
    onEditorChange(data: any) {
        // change my data
        this.setData(data);
    }

}
