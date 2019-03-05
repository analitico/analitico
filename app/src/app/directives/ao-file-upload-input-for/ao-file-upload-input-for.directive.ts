/**
 * Attach input and drag and drop behaviour for file.
 * Must be attached to a upload queue
 */
import {
    Directive,
    ElementRef,
    EventEmitter,
    HostListener,
    Input,
    Output,
} from '@angular/core';

/**
 * A material design file upload queue component.
 */
@Directive({
    selector: 'input[fileUploadInputFor], [fileUploadInputFor]',
})
export class AoFileUploadInputForDirective {


    private _queue: any = null;
    private _element: HTMLElement;
    // optional function to get the upload url
    @Input() getUploadUrl: any;
    @Input() uploadUrl: any;
    @Input() uploaded: any;

    @Output() public onFileSelected: EventEmitter<File[]> = new EventEmitter<File[]>();

    constructor(private element: ElementRef) {
        this._element = this.element.nativeElement;
    }


    @Input('fileUploadInputFor')
    set fileUploadQueue(value: any) {
        if (value) {
            this._queue = value;
        }
    }

    @HostListener('change', ['$event'])
    public onChange(event: any): any {
        if (this.element && this.element.nativeElement && this.element.nativeElement.files) {
            const files = this.element.nativeElement.files;
            this.onFileSelected.emit(files);
            this.addFilesToQueue(files);
            this.element.nativeElement.value = '';
        }
    }

    @HostListener('drop', ['$event'])
    public onDrop(event: any): any {
        event.preventDefault();
        event.stopPropagation();
        const files = event.dataTransfer.files;
        this.onFileSelected.emit(files);
        this.addFilesToQueue(files);

    }

    addFilesToQueue(files) {
        for (let i = 0; i < files.length; i++) {
            if (this.uploadUrl) {
                this._queue.add(files[i], this.uploadUrl, this.uploaded);
            } else if (this.getUploadUrl) {
                // get the url
                this.getUploadUrl(files[i])
                    .then((data) => {
                        this._queue.add(data.file, data.url, this.uploaded);
                    })
                    .catch(() => { });
            }
        }
    }

    @HostListener('dragover', ['$event'])
    public onDropOver(event: any): any {
        event.preventDefault();
    }

}
