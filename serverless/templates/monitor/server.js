"use strict";

// Constants
const PORT = 8080;
const HOST = "0.0.0.0";
const configurationUrl = "./config.json";
const slacWebhookUri = "https://hooks.slack.com/services/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";

const express = require("express");
const cron = require("node-cron");
const moment = require("moment");
const fs = require("fs");
const request = require("request");
const Validator = require("jsonschema").Validator;
const validator = new Validator();
const Slack = require("slack-node");

const slack = new Slack();
slack.setWebhook(slacWebhookUri);

let monitoringTasks = [];
let monitoringTasksDict = {};
let status = {
    status: "ok",
    errors: [],
    lastCheckAt: {}
};
// App
const app = express();

/**
 * Health check: if we have collected some error, the status is 500
 */
app.get("/", (req, res) => {
    if (status.status !== "ok") {
        res.status(500).send(status);
    }
    else {
        res.send(status);
    }
});

/**
 * Allows to reset the status
 */
app.get("/reset", (req, res) => {
    status = {
        status: "ok",
        errors: []
    }
    res.send(status);
});

app.listen(PORT, HOST);


/**
 * Get monitoring configuration
 */
function getConfiguration() {
    // load from file
    return new Promise((resolve, reject) => {
        fs.readFile(configurationUrl, function (err, contents) {
            if (err) {
                return reject(err);
            }
            try {
                // parse
                const parsed = JSON.parse(contents);
                resolve(parsed);
            }
            catch (err) {
                return reject(err);
            }
        })
    })
}

/**
 * Stop all monitoring
 */
function destroyAllTasks() {
    monitoringTasks.forEach(task => {
        task.destroy();
    });
    monitoringTasks = [];
    monitoringTasksDict = {};
}

/**
 * Returns a function that will execute the task
 * It makes the HTTP request and validates the response with the provided schema
 * If errors occur it notifies using slack.
 * @param {*} taskConfig 
 */
function getCronFunction(taskConfig, options) {
    return () => {
        let name = taskConfig.name;
        const isStaging = options && options.staging;
        if (isStaging) {
            // add suffix
            name = `${name}-staging`;
        }
        let url = taskConfig.url;
        if (isStaging) {
            // use staging url
            url = taskConfig.stagingUrl;
        }
        const method = taskConfig.method || "GET";
        const data = taskConfig.data;
        const authorization = taskConfig.authorization;
        const schema = taskConfig.schema;
        const requestMaxTime = taskConfig.requestMaxTime || 5000;
        const payload = {
            method: method,
            uri: url,
            time: true,
            json: true
        };
        if (method === "POST") {
            payload.json = data;
        }
        if (authorization && authorization.bearerToken) {
            payload.auth = {
                "bearer": authorization.bearerToken
            };
        }
        try {
            request(payload, function (error, response, body) {
                try {
                    if (error) {
                        throw error;
                    }
                    status.lastCheckAt[name] = moment().format("YYYY-MM-DDTHH:mm:ssZZ");

                    // check status code
                    if(response.statusCode !== 200){
                        triggerError(`${name}: status code ${response.statusCode}, body ${body}`, taskConfig, isStaging);
                    }
                    // check if body is present
                    if(!body){
                        triggerError(`${name}: empty body!`, taskConfig, isStaging);
                    }

                    if (response.timingPhases.total > requestMaxTime) {
                        // only notify, not error
                        notifyOnSlack(`${name}: exceeded max time ${response.elapsedTime}ms (max time: ${requestMaxTime}ms)`);
                    }

                    const result = validator.validate(body, schema);
                    if (!result.valid) {
                        const errors = result.errors;
                        // if it is staging, only notify without setting error
                        triggerError(`${name}: ${errors}`, taskConfig, isStaging);
                    }
                    else {
                        //console.log(`${name}: ok`)

                    }
                }
                catch (error) {
                    triggerError(`${name}: ${error}`, taskConfig, isStaging);
                }
            })
        }
        catch (error) {
            triggerError(`${name}: request errror ${error}`);
        }
    }
}

/**
 * Schedule all the tasks
 */
function setupMonitoring() {
    getConfiguration()
        .then((configuration) => {
            // destroy all current tasks
            destroyAllTasks();
            // for each configuration, create a cron
            const tasks = configuration.tasks;
            notifyOnSlack(`Configuring ${tasks.length} monitoring tasks...`);
            tasks.forEach(taskConfig => {
                const name = taskConfig.name;
                const schedule = taskConfig.schedule;

                if (monitoringTasksDict[name]) {
                    triggerError(`Duplicate name: ${name}, skipped`);
                    return true;
                }
                if (!cron.validate(schedule)) {
                    triggerError(`Invalid schedule ${schedule} for ${name}, skipped`);
                    return true;
                }
                const cronFunction = getCronFunction(taskConfig);
                // execute immediately
                cronFunction();
                const task = cron.schedule(schedule, cronFunction, { scheduled: true });

                monitoringTasks.push(task);
                monitoringTasksDict[name] = task;

                if (taskConfig.stagingUrl) {
                    // if it has a staging url, configure the staging check
                    const cronStagingFunction = getCronFunction(taskConfig, { staging: true });
                    // execute immediately
                    cronStagingFunction();
                    const taskStaging = cron.schedule(schedule, cronStagingFunction, { scheduled: true });
                    monitoringTasks.push(taskStaging);
                    monitoringTasksDict[`${name}-staging`] = taskStaging;
                }
            });
        })
        .catch((e) => {
            triggerError(e);
        })
}

/**
 * Log errors on console and on slack
 * Set error status for pingdom
 * @param {*} message 
 * @param {*} taskConfig 
 */
function triggerError(message, taskConfig, onlyNotify) {
    // add current timestamp
    const date = moment().format("YYYY-MM-DDTHH:mm:ssZZ");
    message = `${date}: ${message} ${taskConfig ? taskConfig.url : ""}`;
    console.error(message);
    if (!onlyNotify) {
        setErrorStatus(message);
    }
    notifyOnSlack(message);
}
/**
 * Send a slack notification
 * @param {*} message 
 */
function notifyOnSlack(message) { 
    slack.webhook({
        username: "monitor",
        text: message
    }, function (err, response) {
        if (err) {
            setErrorStatus(err);
        }
    });
}

/**
 * Set the error status
 * @param {*} error 
 */
function setErrorStatus(error) {
    status.status = "error";
    status.errors = status.errors.concat(error);
}

// setup monitors
setupMonitoring();