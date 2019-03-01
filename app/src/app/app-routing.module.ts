import { NgModule } from '@angular/core';
import { Routes, RouterModule, RouteReuseStrategy } from '@angular/router';
import { AoDatasetsViewComponent } from 'src/app/components/ao-datasets-view/ao-datasets-view.component';
import { AoDatasetViewComponent } from 'src/app/components/ao-dataset-view/ao-dataset-view.component';
import { AoGroupWsViewComponent } from './components/ao-group-ws-view/ao-group-ws-view.component';
import { AoModelsViewComponent } from './components/ao-models-view/ao-models-view.component';
import { AoModelViewComponent } from './components/ao-model-view/ao-model-view.component';
import { AoRecipeViewComponent } from './components/ao-recipe-view/ao-recipe-view.component';
import { AoEndpointViewComponent } from './components/ao-endpoint-view/ao-endpoint-view.component';
import { AoHomeViewComponent } from './components/ao-home-view/ao-home-view.component';

const routes: Routes = [
    { path: '', component: AoHomeViewComponent },
    { path: 'datasets', component: AoDatasetsViewComponent },
    { path: 'recipes', component: AoGroupWsViewComponent },
    { path: 'models', component: AoModelsViewComponent },
    { path: 'endpoints', component: AoGroupWsViewComponent },
    { path: 'datasets/:id', component: AoDatasetViewComponent },
    { path: 'recipes/:id', component: AoRecipeViewComponent },
    { path: 'models/:id', component: AoModelViewComponent },
    { path: 'endpoints/:id', component: AoEndpointViewComponent }
];

@NgModule({
    imports: [RouterModule.forRoot(routes, { onSameUrlNavigation: 'reload' })],
    exports: [RouterModule],
    /*providers: [{
        provide: RouteReuseStrategy,
        useClass: AoDoNotReuseRouteStrategy
      }] */
})
export class AppRoutingModule { }
