import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { AoDatasetsViewComponent } from 'src/app/components/ao-datasets-view/ao-datasets-view.component';
import { AoDatasetViewComponent } from 'src/app/components/ao-dataset-view/ao-dataset-view.component';
import { AoGroupWsViewComponent } from './components/ao-group-ws-view/ao-group-ws-view.component';
import { AoModelsViewComponent } from './components/ao-models-view/ao-models-view.component';

const routes: Routes = [
    { path: 'datasets', component: AoDatasetsViewComponent },
    { path: 'recipes', component: AoGroupWsViewComponent },
    { path: 'models', component: AoModelsViewComponent },
    { path: 'endpoints', component: AoGroupWsViewComponent },
    { path: 'datasets/:id', component: AoDatasetViewComponent }

];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})
export class AppRoutingModule { }
