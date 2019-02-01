import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { AoDatasetViewComponent } from 'src/app/components/ao-dataset-view/ao-dataset-view.component';

const routes: Routes = [
    { path: 'datasets/:id', component: AoDatasetViewComponent },
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})
export class AppRoutingModule { }
